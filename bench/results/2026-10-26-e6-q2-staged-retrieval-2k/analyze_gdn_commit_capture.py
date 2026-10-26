#!/usr/bin/env python3
"""Compare two sequential STGCMT1 all-layer GDN commit captures."""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiqQQii')


def records(path: Path) -> list[dict]:
    result = []
    with path.open('rb') as f:
        while True:
            offset = f.tell()
            header = f.read(HEADER.size)
            if not header:
                break
            if len(header) != HEADER.size:
                raise ValueError('truncated STGCMT1 header')
            magic, version, layer, position, recurrent, count, token, slot = HEADER.unpack(header)
            if magic != b'STGCMT1\0' or version != 1:
                raise ValueError(f'unsupported record at byte {offset}: {magic!r}/{version}')
            data_offset = f.tell()
            payload_bytes = count * 4
            if len(f.read(payload_bytes)) != payload_bytes:
                raise ValueError(f'truncated float payload at byte {data_offset}')
            result.append({'offset': offset, 'data_offset': data_offset, 'layer': layer,
                           'position': position, 'recurrent_floats': recurrent,
                           'state_floats': count, 'token': token, 'slot': slot})
    if len(result) == 0 or len(result) % 2:
        raise ValueError('expected two equal non-empty sequential captures')
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('capture', type=Path, help='concatenated reference then candidate records')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    rows = records(args.capture)
    half = len(rows) // 2
    output = []
    total_n = total_diff = 0
    total_delta2 = total_ref2 = 0.0
    with args.capture.open('rb') as f:
        for reference, candidate in zip(rows[:half], rows[half:]):
            for key in ('layer', 'position', 'recurrent_floats', 'state_floats', 'token'):
                if reference[key] != candidate[key]:
                    raise ValueError(f'paired record mismatch for {key}: {reference} vs {candidate}')
            count = reference['state_floats']
            f.seek(reference['data_offset'])
            left = struct.unpack(f'<{count}f', f.read(count * 4))
            f.seek(candidate['data_offset'])
            right = struct.unpack(f'<{count}f', f.read(count * 4))
            delta2 = reference2 = 0.0
            different = 0
            max_abs = 0.0
            for x, y in zip(left, right):
                delta = y - x
                different += delta != 0.0
                delta2 += delta * delta
                reference2 += x * x
                max_abs = max(max_abs, abs(delta))
            output.append({'layer': reference['layer'], 'position': reference['position'],
                           'token': reference['token'], 'state_floats': count,
                           'different_floats': different,
                           'relative_l2': math.sqrt(delta2 / reference2) if reference2 else math.sqrt(delta2),
                           'max_abs_delta': max_abs})
            total_n += count
            total_diff += different
            total_delta2 += delta2
            total_ref2 += reference2
    summary = {'schema': 1, 'format': 'STGCMT1', 'reference_records': half,
               'candidate_records': half, 'total_floats': total_n,
               'different_floats': total_diff,
               'fraction_different': total_diff / total_n,
               'global_relative_l2': math.sqrt(total_delta2 / total_ref2) if total_ref2 else math.sqrt(total_delta2),
               'layers': output}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ('reference_records', 'candidate_records', 'total_floats',
                                               'different_floats', 'global_relative_l2')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
