#!/usr/bin/env python3
"""Pair STGDIAG4 GDN layer rows and report the first changed captured field."""
import json
import math
from pathlib import Path
import struct
import sys

HEADER = struct.Struct('<8sIiiqQQQQQ8i')
HEADER_V5 = struct.Struct('<8sIiiqQQQQQ8q8i8i')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')

def read_rows(path):
    data = Path(path).read_bytes()
    offset = 0
    rows = []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError(f'{path}: truncated header at {offset}')
        magic = data[offset:offset + 8]
        if magic == b'STGDIAG4':
            if offset + HEADER.size > len(data):
                raise ValueError(f'{path}: truncated STGDIAG4 header at {offset}')
            magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
            positions = [pos0 + row for row in range(8)]
            slots = [-1] * 8
            header_size = HEADER.size
        elif magic == b'STGDIAG5':
            if offset + HEADER_V5.size > len(data):
                raise ValueError(f'{path}: truncated STGDIAG5 header at {offset}')
            values = HEADER_V5.unpack_from(data, offset)
            magic, version, layer, count, pos0, n, c, hv, zv, state_n = values[:10]
            positions = values[10:18]
            slots = values[18:26]
            tokens = values[26:34]
            header_size = HEADER_V5.size
        else:
            raise ValueError(f'{path}: unsupported STGDIAG record at {offset}')
        if version not in (4, 5) or not 0 < count <= 8:
            raise ValueError(f'{path}: invalid STGDIAG record at {offset}')
        offset += header_size
        dims = (n, c, c, hv, hv, zv, zv, n, n, n)
        arrays = []
        for dim in dims:
            size = count * dim * 4
            if offset + size > len(data):
                raise ValueError(f'{path}: truncated {FIELDS[len(arrays)]} array')
            arrays.append(struct.unpack_from(f'<{count * dim}f', data, offset))
            offset += size
        for row in range(count):
            fields = {name: array[row * dim:(row + 1) * dim]
                      for name, array, dim in zip(FIELDS, arrays, dims)}
            rows.append({'position': positions[row], 'slot': slots[row], 'token': tokens[row],
                         'layer': layer, 'fields': fields})
    return rows

def delta(a, b):
    diff = [x - y for x, y in zip(a, b)]
    return {'exact': a == b,
            'different_values': sum(x != y for x, y in zip(a, b)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in diff) /
                                     max(math.fsum(x * x for x in a), 1e-300)),
            'max_abs': max((abs(x) for x in diff), default=0.0)}

def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: compare_layer_capture.py SERIAL.stgdiag BATCH.stgdiag')
    serial = read_rows(sys.argv[1])
    batch = read_rows(sys.argv[2])
    serial_map = {}
    batch_map = {}
    for rows, target in ((serial, serial_map), (batch, batch_map)):
        for row in rows:
            target.setdefault((row['position'], row['token']), []).append(row)
    common = sorted(serial_map.keys() & batch_map.keys())
    comparisons = []
    for key in common:
        for occurrence, (a, b) in enumerate(zip(serial_map[key], batch_map[key])):
            changes = {field: delta(a['fields'][field], b['fields'][field])
                       for field in FIELDS if a['fields'][field] != b['fields'][field]}
            comparisons.append({'position': key[0], 'token': key[1], 'occurrence': occurrence,
                                'serial_slot': a['slot'], 'batch_slot': b['slot'],
                                'changed_fields': changes})
    first = next((item for item in comparisons if item['changed_fields']), None)
    print(json.dumps({'serial_rows': len(serial), 'batch_rows': len(batch),
                      'common_position_token_pairs': len(common),
                      'paired_occurrences': len(comparisons),
                      'serial_range': [min(r['position'] for r in serial), max(r['position'] for r in serial)] if serial else None,
                      'batch_range': [min(r['position'] for r in batch), max(r['position'] for r in batch)] if batch else None,
                      'serial_keys': [[r['position'], r['token']] for r in serial],
                      'batch_selected_keys': [[r['position'], r['token']] for r in batch
                                              if 115 <= r['position'] <= 130],
                      'first_changed_row': first,
                      'requested_position_comparisons': [item for item in comparisons
                          if item['position'] in (118, 119, 120)]}, indent=2))

if __name__ == '__main__':
    main()
