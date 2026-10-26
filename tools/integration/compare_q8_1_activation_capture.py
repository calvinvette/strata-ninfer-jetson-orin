#!/usr/bin/env python3
"""Compare Q8_1 representations of paired verifier MoE input captures."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct

from q2_0_expert_oracle import quantize_q8_1


HEADER = struct.Struct('<8sIIIIQq8i')


def read_capture(path: Path) -> dict[tuple[int, int], tuple[float, ...]]:
    raw = path.read_bytes()
    records: dict[tuple[int, int], tuple[float, ...]] = {}
    offset = 0
    width = None
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f'{path}: truncated input header at byte {offset}')
        h = HEADER.unpack_from(raw, offset)
        if h[0] != b'STMOINP1' or h[1] != 1:
            raise ValueError(f'{path}: unsupported input capture header {h[:2]}')
        rows, n_embd, pos0, tokens = h[3], h[5], h[6], h[7:]
        if rows <= 0 or n_embd <= 0 or n_embd % 32:
            raise ValueError(f'{path}: invalid row count or Q8_1 width')
        if width is not None and width != n_embd:
            raise ValueError(f'{path}: hidden width changes between records')
        width = n_embd
        count = rows * n_embd
        end = offset + HEADER.size + count * 4
        if end > len(raw):
            raise ValueError(f'{path}: truncated float payload at byte {offset}')
        values = struct.unpack_from(f'<{count}f', raw, offset + HEADER.size)
        for row in range(rows):
            position = pos0 + row
            token = tokens[row] if row < len(tokens) else None
            key = (position, token)
            if key in records:
                raise ValueError(f'{path}: duplicate position/token record {key}')
            records[key] = values[row * n_embd:(row + 1) * n_embd]
        offset = end
    if not records:
        raise ValueError(f'{path}: no input records')
    return records


def f32_metrics(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    delta = [b - a for a, b in zip(reference, candidate)]
    norm = math.sqrt(math.fsum(x * x for x in reference))
    return {
        'count': len(reference),
        'different': sum(a != b for a, b in zip(reference, candidate)),
        'relative_l2': math.sqrt(math.fsum(x * x for x in delta)) / max(norm, 1e-300),
        'max_abs': max((abs(x) for x in delta), default=0.0),
    }


def compare_vectors(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate):
        raise ValueError('activation widths differ')
    if not reference or len(reference) % 32:
        raise ValueError('activation width must be a nonzero multiple of 32')
    ref_blocks = quantize_q8_1(reference)
    cand_blocks = quantize_q8_1(candidate)
    changed_blocks = []
    changed_codes = 0
    changed_scales = 0
    for block, (a, b) in enumerate(zip(ref_blocks, cand_blocks)):
        code_delta = sum(x != y for x, y in zip(a[0], b[0]))
        scale_changed = a[1] != b[1]
        changed_codes += code_delta
        changed_scales += int(scale_changed)
        if code_delta or scale_changed:
            changed_blocks.append({
                'block': block,
                'code_values_different': code_delta,
                'reference_scale': a[1],
                'candidate_scale': b[1],
                'scale_different': scale_changed,
            })
    return {
        'f32': f32_metrics(reference, candidate),
        'q8_1': {
            'block_count': len(ref_blocks),
            'integer_codes_different': changed_codes,
            'scales_different': changed_scales,
            'different_blocks': changed_blocks,
        },
    }


def compare_captures(reference_path: Path, candidate_path: Path,
                     positions: list[int] | None = None) -> dict:
    reference = read_capture(reference_path)
    candidate = read_capture(candidate_path)
    if reference.keys() != candidate.keys():
        missing = sorted(reference.keys() ^ candidate.keys())
        raise ValueError(f'capture position/token identities differ: {missing[:8]}')
    wanted = set(positions) if positions is not None else None
    results = []
    for position, token in sorted(reference):
        if wanted is not None and position not in wanted:
            continue
        results.append({
            'position': position,
            'token_id': token,
            **compare_vectors(reference[(position, token)], candidate[(position, token)]),
        })
    if not results:
        raise ValueError('no captured rows matched the requested positions')
    return {
        'schema': 1,
        'format': 'STMO input; Q8_1 via q2_0_expert_oracle.quantize_q8_1',
        'reference': str(reference_path),
        'candidate': str(candidate_path),
        'positions': results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--position', type=int, action='append', dest='positions',
                        help='limit to a captured token position; repeatable')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = compare_captures(args.reference, args.candidate, args.positions)
    encoded = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
