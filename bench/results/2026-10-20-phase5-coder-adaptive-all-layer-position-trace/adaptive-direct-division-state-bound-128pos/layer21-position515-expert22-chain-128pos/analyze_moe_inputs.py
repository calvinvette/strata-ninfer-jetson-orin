#!/usr/bin/env python3
"""Compare per-layer verifier MoE inputs in same-position initial/recovery captures."""
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIIIIQq8i')

def read(path):
    data = path.read_bytes()
    records = []
    off = 0
    while off < len(data):
        if len(data) - off < HEADER.size:
            raise ValueError(f'truncated header at {off}')
        magic, version, layer, rows, reserved, width, pos0, *tokens = HEADER.unpack_from(data, off)
        if magic != b'STMOINP1' or version != 1 or reserved != 0 or rows != 1 or width == 0:
            raise ValueError(f'unexpected header: {(magic, version, layer, rows, reserved, width, pos0)}')
        off += HEADER.size
        size = width * rows * 4
        if off + size > len(data):
            raise ValueError(f'truncated payload at {off}')
        raw = data[off:off + size]
        values = struct.unpack(f'<{width}f', raw)
        records.append({'layer': layer, 'position': pos0, 'token': tokens[0], 'raw': raw, 'values': values})
        off += size
    return data, records

def diff(a, b):
    if len(a) != len(b): raise ValueError('width mismatch')
    count = 0; max_abs = 0.0; delta2 = 0.0; ref2 = 0.0
    for x, y in zip(a, b):
        d = abs(x-y)
        if d: count += 1
        max_abs = max(max_abs, d); delta2 += d*d; ref2 += x*x
    return {'values': len(a), 'different_values': count, 'max_abs_diff': max_abs,
            'relative_l2': math.sqrt(delta2/ref2) if ref2 else None}

def main():
    root = Path(__file__).parent
    result = {'scope': 'raw verifier MoE input capture, initial short request versus recovery short request', 'arms': {}}
    for arm in ('adaptive-cap8', 'delayed-control'):
        raw, records = read(root / arm / 'result/verify-moe-input.bin')
        initial = {r['layer']: r for r in records[:48]}
        recovery = {r['layer']: r for r in records[-48:]}
        if len(initial) != 48 or len(recovery) != 48:
            raise ValueError(f'{arm}: expected 48 layers per captured request, found {len(records)} total')
        if set(initial) != set(range(48)) or set(recovery) != set(range(48)):
            raise ValueError(f'{arm}: layer sequence mismatch')
        layers = []
        for layer in range(48):
            a, b = initial[layer], recovery[layer]
            if (a['position'], a['token']) != (b['position'], b['token']):
                raise ValueError(f'{arm}/layer {layer}: token key mismatch')
            row = {'layer': layer, 'position': a['position'], 'token_id': a['token'], **diff(a['values'], b['values'])}
            row['initial_sha256'] = hashlib.sha256(a['raw']).hexdigest()
            row['recovery_sha256'] = hashlib.sha256(b['raw']).hexdigest()
            layers.append(row)
        result['arms'][arm] = {'capture_bytes': len(raw), 'record_count': len(records),
                               'raw_sha256': hashlib.sha256(raw).hexdigest(),
                               'first_differing_layer': next((x['layer'] for x in layers if x['different_values']), None),
                               'different_layers': [x for x in layers if x['different_values']]}
    out = root / 'moe-input-analysis.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({arm: {'first_differing_layer': val['first_differing_layer'],
                            'different_layers': [(x['layer'], x['different_values'], x['relative_l2']) for x in val['different_layers'][:8]]}
                      for arm, val in result['arms'].items()}, indent=2))

if __name__ == '__main__': main()
