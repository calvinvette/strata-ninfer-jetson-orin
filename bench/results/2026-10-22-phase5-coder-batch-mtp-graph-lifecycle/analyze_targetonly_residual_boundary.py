#!/usr/bin/env python3
"""Compare serial and one-row batch STBNDY2 residual/read captures."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--capture', type=Path, required=True)
parser.add_argument('--layer', type=int, default=10)
parser.add_argument('--position', type=int, default=119)
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
            raise ValueError('truncated STBNDY2 header')
        magic, version, layer, position, n, hc, token, slot = HEADER.unpack_from(data, offset)
        if magic != b'STBNDY2\0' or version != 2 or layer != args.layer:
            raise ValueError(f'invalid STBNDY2 header: {magic!r}, {version}, layer={layer}')
        offset += HEADER.size
        counts = (hc * n, n, hc, hc * n, n, hc, hc * n, hc * n)
        values = {}
        for name, count in zip(FIELDS, counts):
            size = count * 4
            if offset + size > len(data):
                raise ValueError('truncated STBNDY2 payload')
            values[name] = data[offset:offset + size]
            offset += size
        rows.append({'position': position, 'layer': layer, 'n': n, 'hc': hc,
                     'token': token, 'slot': slot, 'fields': values})
    return rows

def compare(serial, batch):
    av = struct.unpack(f'<{len(serial)//4}f', serial)
    bv = struct.unpack(f'<{len(batch)//4}f', batch)
    delta = [a - b for a, b in zip(av, bv)]
    denom = math.sqrt(math.fsum(a*a for a in av))
    return {'values': len(av), 'different_values': sum(a != b for a, b in zip(av, bv)),
            'max_abs': max(map(abs, delta), default=0.0),
            'relative_l2': math.sqrt(math.fsum(x*x for x in delta)) / denom if denom else 0.0,
            'serial_sha256': hashlib.sha256(serial).hexdigest(),
            'batch_sha256': hashlib.sha256(batch).hexdigest()}

rows = [r for r in read_records(args.capture) if r['position'] == args.position]
serial = [r for r in rows if r['slot'] == -1]
batch = [r for r in rows if r['slot'] >= 0]
if len(serial) != 1 or len(batch) != 1:
    raise ValueError(f'expected one serial and one batch row at position {args.position}; '
                     f'found serial={len(serial)}, batch={len(batch)}')
serial, batch = serial[0], batch[0]
if serial['token'] != batch['token'] or (serial['n'], serial['hc']) != (batch['n'], batch['hc']):
    raise ValueError('serial and batch records do not have matching token and dimensions')
comparisons = {name: compare(serial['fields'][name], batch['fields'][name]) for name in FIELDS}
result = {'capture': str(args.capture), 'layer': args.layer, 'position': args.position,
          'token': serial['token'], 'serial_slot': -1, 'batch_slot': batch['slot'],
          'dimensions': {'n_embd': serial['n'], 'hc': serial['hc']},
          'first_different_field': next((name for name in FIELDS
                                         if comparisons[name]['different_values']), None),
          'fields': comparisons}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'position': args.position, 'token': result['token'],
                  'first_different_field': result['first_different_field'],
                  'fields': {name: {key: row[key] for key in
                                    ('different_values', 'max_abs', 'relative_l2')}
                             for name, row in comparisons.items()}}, indent=2))
