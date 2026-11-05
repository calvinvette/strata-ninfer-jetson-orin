#!/usr/bin/env python3
"""Compare Q8_1 representations of paired raw float32 activation rows."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct

from q2_0_expert_oracle import quantize_q8_1


def read_row(path: Path, width: int) -> tuple[float, ...]:
    raw = path.read_bytes()
    if len(raw) != width * 4:
        raise ValueError(f'{path}: expected {width * 4} bytes, got {len(raw)}')
    values = struct.unpack(f'<{width}f', raw)
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f'{path}: non-finite float32 activation value')
    return values


def compare(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate) or not reference or len(reference) % 32:
        raise ValueError('activation widths must match and be a nonzero multiple of 32')
    ref_blocks, cand_blocks = quantize_q8_1(reference), quantize_q8_1(candidate)
    changed = []
    total_codes = total_scales = 0
    for index, (ref, cand) in enumerate(zip(ref_blocks, cand_blocks)):
        code_differences = sum(a != b for a, b in zip(ref[0], cand[0]))
        scale_differs = ref[1] != cand[1]
        total_codes += code_differences
        total_scales += int(scale_differs)
        if code_differences or scale_differs:
            changed.append({
                'block': index,
                'code_values_different': code_differences,
                'reference_scale': ref[1],
                'candidate_scale': cand[1],
                'scale_different': scale_differs,
            })
    delta = [b - a for a, b in zip(reference, candidate)]
    norm = math.sqrt(math.fsum(value * value for value in reference))
    return {
        'width': len(reference),
        'f32': {
            'different_values': sum(a != b for a, b in zip(reference, candidate)),
            'relative_l2': math.sqrt(math.fsum(value * value for value in delta)) / max(norm, 1e-300),
            'max_abs': max(abs(value) for value in delta),
        },
        'q8_1': {
            'block_count': len(ref_blocks),
            'blocks_different': len(changed),
            'integer_code_differences': total_codes,
            'scale_differences': total_scales,
            'different_blocks': changed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--width', type=int, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.width <= 0 or args.width % 32:
        parser.error('--width must be a positive multiple of 32')
    result = {
        'format': 'raw little-endian float32 rows; independent Q8_1 oracle from q2_0_expert_oracle.py',
        'reference': str(args.reference),
        'candidate': str(args.candidate),
        **compare(read_row(args.reference, args.width), read_row(args.candidate, args.width)),
    }
    encoded = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
