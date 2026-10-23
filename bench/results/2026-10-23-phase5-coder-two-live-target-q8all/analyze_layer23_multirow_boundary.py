#!/usr/bin/env python3
"""Pair multirow STBNDY2 records by position and token, then compare their fields."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--serial', type=Path, required=True)
parser.add_argument('--batch', type=Path, required=True)
parser.add_argument('--layer', type=int, default=23)
parser.add_argument('--position', type=int, default=105)
parser.add_argument('--batch-slot', type=int,
                     help='disambiguate repeated input tokens at the selected position')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()

HEADER = struct.Struct('<8sIiqQQii')
FIELDS = ('residual_after_layer', 'branch_output_after_layer', 'injection_after_layer',
          'residual_before_next_read', 'branch_output_before_next_read', 'injection_before_next_read',
          'residual_after_next_read', 'normalized_residual_after_next_read')


def read_records(path):
    data = path.read_bytes()
    offset = 0
    rows = []
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError(f'{path}: truncated STBNDY2 header at {offset}')
        magic, version, layer, position, n, hc, token, slot = HEADER.unpack_from(data, offset)
        if magic != b'STBNDY2\0' or version != 2 or layer != args.layer:
            raise ValueError(f'{path}: invalid header {magic!r}, version={version}, layer={layer}')
        offset += HEADER.size
        counts = (hc * n, n, hc, hc * n, n, hc, hc * n, hc * n)
        values = {}
        for name, count in zip(FIELDS, counts):
            size = count * 4
            if offset + size > len(data):
                raise ValueError(f'{path}: truncated {name} payload at {offset}')
            values[name] = data[offset:offset + size]
            offset += size
        rows.append({'position': position, 'layer': layer, 'n': n, 'hc': hc,
                     'token': token, 'slot': slot, 'fields': values})
    return rows


def compare(left, right):
    a = struct.unpack(f'<{len(left) // 4}f', left)
    b = struct.unpack(f'<{len(right) // 4}f', right)
    delta = [x - y for x, y in zip(a, b)]
    denom = math.sqrt(math.fsum(x * x for x in a))
    return {'values': len(a), 'different_values': sum(x != y for x, y in zip(a, b)),
            'max_abs': max(map(abs, delta), default=0.0),
            'relative_l2': math.sqrt(math.fsum(x * x for x in delta)) / denom if denom else 0.0,
            'serial_sha256': hashlib.sha256(left).hexdigest(),
            'batch_sha256': hashlib.sha256(right).hexdigest()}


serial = [r for r in read_records(args.serial)
          if r['position'] == args.position and r['slot'] == -1]
if len(serial) != 1:
    raise ValueError(f'expected one serial row, found {len(serial)}')
serial = serial[0]
batch = [r for r in read_records(args.batch)
         if r['position'] == args.position and r['token'] == serial['token']]
if args.batch_slot is not None:
    batch = [r for r in batch if r['slot'] == args.batch_slot]
if len(batch) != 1:
    raise ValueError(f'expected one batch row paired by token {serial["token"]}, found {len(batch)}; '
                     'supply --batch-slot if repeated tokens make pairing ambiguous')
batch = batch[0]
if (serial['n'], serial['hc']) != (batch['n'], batch['hc']):
    raise ValueError('serial and batch dimensions differ')
comparisons = {name: compare(serial['fields'][name], batch['fields'][name]) for name in FIELDS}
result = {'serial_path': str(args.serial), 'batch_path': str(args.batch), 'layer': args.layer,
          'position': args.position, 'token': serial['token'], 'serial_slot': -1,
          'batch_slot': batch['slot'], 'dimensions': {'n_embd': serial['n'], 'hc': serial['hc']},
          'first_different_field': next((name for name in FIELDS
                                         if comparisons[name]['different_values']), None),
          'fields': comparisons,
          'limits': ['pairing uses position and token; repeated tokens require --batch-slot',
                     'one captured position and one request pair do not localize the originating operation']}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'position': args.position, 'token': result['token'],
                  'serial_slot': -1, 'batch_slot': result['batch_slot'],
                  'first_different_field': result['first_different_field'],
                  'fields': {name: {key: row[key] for key in
                                    ('different_values', 'max_abs', 'relative_l2')}
                             for name, row in comparisons.items()}}, indent=2))
