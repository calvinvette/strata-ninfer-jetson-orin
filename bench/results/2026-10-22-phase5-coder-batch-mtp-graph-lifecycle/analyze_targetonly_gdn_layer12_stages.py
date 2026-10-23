#!/usr/bin/env python3
"""Compare serial and delayed-batch layer-12 STGDIAG5 rows."""
import hashlib
import json
import math
import argparse
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--layer', type=int, default=12)
parser.add_argument('--run', type=Path, default=ROOT / 'run-targetonly-layer12-stage-119')
args = parser.parse_args()
CAPTURE = args.run.resolve() / f'layer{args.layer}.stgdiag'
OUTPUT = ROOT / f'targetonly-layer{args.layer}-stage-119-analysis.json'
HEADER = struct.Struct('<8sIiiqQQQQQ8q8i8i')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')

def records(path):
    data = path.read_bytes()
    offset = 0
    found = []
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError('truncated STGDIAG5 header')
        h = HEADER.unpack_from(data, offset)
        magic, version, layer, rows, pos0, n, c, hv, zv, state_floats = h[:10]
        positions, slots, tokens = h[10:18], h[18:26], h[26:34]
        if magic != b'STGDIAG5' or version != 5 or layer != args.layer or rows <= 0 or n != 2560:
            raise ValueError(f'invalid stage capture header: {h[:10]}')
        offset += HEADER.size
        row_bytes = (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        for row in range(rows):
            start = offset + row * row_bytes
            lengths = (n, c, c, hv, hv, zv, zv, n, n, n)
            values = {}
            cursor = start
            for name, count in zip(FIELDS, lengths):
                size = count * 4
                values[name] = data[cursor:cursor + size]
                cursor += size
            found.append({'position': positions[row], 'slot': slots[row], 'token': tokens[row],
                          'dims': dict(n=n, c=c, hv=hv, zv=zv), 'fields': values})
        offset += rows * row_bytes
    return found

rows = records(CAPTURE)
serial = [row for row in rows if row['slot'] == -1 and row['position'] == 119]
batch = [row for row in rows if row['slot'] == 0 and row['position'] == 119]
if len(serial) != 1 or len(batch) != 1 or serial[0]['token'] != batch[0]['token']:
    raise ValueError('expected one serial and one batch slot-0 row for the same token at position 119')

comparisons = {}
for name in FIELDS:
    a = serial[0]['fields'][name]
    b = batch[0]['fields'][name]
    av = struct.unpack(f'<{len(a) // 4}f', a)
    bv = struct.unpack(f'<{len(b) // 4}f', b)
    delta = [x - y for x, y in zip(av, bv)]
    denom = math.sqrt(math.fsum(x * x for x in av))
    comparisons[name] = {
        'values': len(av),
        'different_values': sum(x != y for x, y in zip(av, bv)),
        'max_abs': max(map(abs, delta), default=0.0),
        'relative_l2': math.sqrt(math.fsum(x * x for x in delta)) / denom if denom else 0.0,
        'serial_sha256': hashlib.sha256(a).hexdigest(),
        'batch_sha256': hashlib.sha256(b).hexdigest(),
    }

result = {'capture': str(CAPTURE.relative_to(ROOT.parent)),
          'layer': args.layer, 'position': 119, 'token': serial[0]['token'],
          'serial_slot': -1, 'batch_slot': 0, 'dimensions': serial[0]['dims'],
          'first_different_field': next((name for name in FIELDS
                                         if comparisons[name]['different_values']), None),
          'fields': comparisons}
OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'position': 119, 'token': result['token'],
                  'first_different_field': result['first_different_field'],
                  'fields': {name: {'different_values': value['different_values'],
                                    'max_abs': value['max_abs'],
                                    'relative_l2': value['relative_l2']}
                             for name, value in comparisons.items()}}, indent=2))
