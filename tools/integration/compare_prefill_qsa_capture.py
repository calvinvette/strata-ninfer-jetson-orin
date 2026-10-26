#!/usr/bin/env python3
"""Compare opt-in prompt-prefill QSA captures."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct


HEADER = struct.Struct('<8sIiqQQQQQii')


def read_capture(path: Path) -> tuple[dict, dict[str, tuple[float, ...]], tuple[int, ...]]:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise ValueError(f'{path}: truncated QSA prefill header')
    (magic, version, layer, position, n_embd, q_width, idx_width, kv_width,
     cap, token, reserved) = HEADER.unpack_from(raw)
    if magic != b'STQPFD1\0' or version != 1:
        raise ValueError(f'{path}: unsupported QSA prefill capture')
    if min(n_embd, q_width, idx_width, kv_width, cap) <= 0:
        raise ValueError(f'{path}: invalid dimensions')
    float_count = 2 * n_embd + 2 * q_width + idx_width + 2 * kv_width
    expected = HEADER.size + float_count * 4 + cap * 4 + q_width * 2
    if len(raw) != expected:
        raise ValueError(f'{path}: payload size {len(raw) - HEADER.size}; expected {expected - HEADER.size}')
    offset = HEADER.size

    def floats(name: str, count: int) -> tuple[float, ...]:
        nonlocal offset
        result = struct.unpack_from(f'<{count}f', raw, offset)
        offset += count * 4
        return result

    fields = {
        'qsa_input': floats('qsa_input', n_embd),
        'query': floats('query', q_width),
        'index_query': floats('index_query', idx_width),
        'current_key': floats('current_key', kv_width),
        'current_value': floats('current_value', kv_width),
    }
    selection = struct.unpack_from(f'<{cap}i', raw, offset)
    offset += cap * 4
    fields['attention'] = floats('attention', q_width)
    gated_bits = struct.unpack_from(f'<{q_width}H', raw, offset)
    offset += q_width * 2
    fields['gated_attention_f16'] = tuple(_f16_to_f32(v) for v in gated_bits)
    fields['projected_output'] = floats('projected_output', n_embd)
    if offset != len(raw):
        raise ValueError(f'{path}: parser consumed {offset} of {len(raw)} bytes')
    meta = {'layer': layer, 'position': position, 'n_embd': n_embd,
            'q_width': q_width, 'idx_width': idx_width, 'kv_width': kv_width,
            'cap': cap, 'token': token, 'reserved': reserved}
    return meta, fields, selection


def _f16_to_f32(bits: int) -> float:
    return struct.unpack('<e', struct.pack('<H', bits))[0]


def metrics(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate):
        raise ValueError('QSA field dimensions differ')
    err2 = math.fsum((b - a) ** 2 for a, b in zip(reference, candidate))
    ref2 = math.fsum(a * a for a in reference)
    return {'count': len(reference), 'different': sum(a != b for a, b in zip(reference, candidate)),
            'relative_l2': math.sqrt(err2 / ref2) if ref2 else 0.0,
            'max_abs': max((abs(b - a) for a, b in zip(reference, candidate)), default=0.0)}


def compare(reference: Path, candidate: Path) -> dict:
    ah, a, a_sel = read_capture(reference)
    bh, b, b_sel = read_capture(candidate)
    if ah != bh:
        raise ValueError(f'QSA prefill capture headers differ: {ah} vs {bh}')
    return {'header': ah, 'selection_equal': a_sel == b_sel,
            'selection_reference': a_sel, 'selection_candidate': b_sel,
            'fields': {name: metrics(a[name], b[name]) for name in a}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.reference, args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'layer': result['header']['layer'], 'position': result['header']['position'],
                      'selection_equal': result['selection_equal'],
                      'different_fields': [k for k, v in result['fields'].items() if v['different']]}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
