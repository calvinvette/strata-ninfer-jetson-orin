#!/usr/bin/env python3
"""Pair STGCMT1 committed GDN state by layer, position and consumed token."""
import json
import math
from pathlib import Path
import struct
import sys

HEADER = struct.Struct('<8sIiqQQii')

def read_records(path):
    data = Path(path).read_bytes()
    offset = 0
    records = []
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError(f'{path}: truncated header at {offset}')
        magic, version, layer, position, recurrent, count, token, slot = HEADER.unpack_from(data, offset)
        if magic != b'STGCMT1\0' or version != 1 or not 0 < recurrent <= count:
            raise ValueError(f'{path}: invalid STGCMT1 header at {offset}')
        offset += HEADER.size
        size = count * 4
        if offset + size > len(data):
            raise ValueError(f'{path}: truncated state at {offset}')
        values = struct.unpack_from(f'<{count}f', data, offset)
        offset += size
        records.append({'layer': layer, 'position': position, 'recurrent_floats': recurrent,
                        'token': token, 'slot': slot, 'values': values})
    return records

def delta(a, b):
    if len(a) != len(b):
        raise ValueError('state size mismatch')
    diff = [x - y for x, y in zip(a, b)]
    return {'exact': a == b, 'different_values': sum(x != y for x, y in zip(a, b)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in diff) /
                                     max(math.fsum(x * x for x in a), 1e-300)),
            'max_abs': max((abs(x) for x in diff), default=0.0)}

def main():
    if len(sys.argv) != 4:
        raise SystemExit('usage: compare_gdn_commit_state.py SERIAL0.stgcmt SERIAL1.stgcmt BATCH.stgcmt')
    serial = [read_records(path) for path in sys.argv[1:3]]
    batch = read_records(sys.argv[3])
    maps = []
    for rows in serial:
        mapping = {}
        for row in rows:
            mapping.setdefault((row['layer'], row['position'], row['token']), []).append(row)
        maps.append(mapping)
    paired = []
    for row in batch:
        key = (row['layer'], row['position'], row['token'])
        comparisons = []
        for prompt, mapping in enumerate(maps):
            candidates = mapping.get(key, [])
            if candidates:
                comparisons.append({'serial_prompt': prompt,
                                    'delta': delta(candidates[0]['values'], row['values'])})
        nearest = min(comparisons, key=lambda item: item['delta']['relative_l2']) if comparisons else None
        paired.append({'layer': row['layer'], 'position': row['position'], 'token': row['token'],
                       'batch_slot': row['slot'], 'serial_comparisons': comparisons,
                       'nearest_serial_prompt': nearest['serial_prompt'] if nearest else None,
                       'nearest_delta': nearest['delta'] if nearest else None})
    print(json.dumps({'serial_records': [len(rows) for rows in serial],
                      'batch_records': len(batch), 'paired_records': sum(bool(x['serial_comparisons']) for x in paired),
                      'records': paired}, indent=2))

if __name__ == '__main__':
    main()
