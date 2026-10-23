#!/usr/bin/env python3
"""Compare captured serial and batch verifier logits at the changed output."""
import heapq
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent / 'logits-position-133'
HEADER = struct.Struct('<8sqiiiIQ')

def read_record(path, slot=None):
    data = path.read_bytes()
    offset = 0
    found = []
    while offset < len(data):
        magic, position, record_slot, row, token, _, vocab = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        logits = struct.unpack_from(f'<{vocab}f', data, offset)
        offset += vocab * 4
        if magic != b'STLOG01\0' or position != 133 or vocab != 248320:
            raise ValueError(f'{path}: unexpected capture record')
        if slot is None or record_slot == slot:
            found.append({'slot': record_slot, 'row': row, 'token': token, 'logits': logits})
    if offset != len(data) or len(found) != 1:
        raise ValueError(f'{path}: expected one selected record, found {len(found)}')
    return found[0]

serial = read_record(ROOT/'serial.bin')
batch = read_record(ROOT/'batch.bin', slot=1)
if serial['token'] != batch['token']:
    raise ValueError(f"input token mismatch: {serial['token']} vs {batch['token']}")
a, b = serial['logits'], batch['logits']
deltas = [x-y for x,y in zip(a,b)]
top = lambda xs: heapq.nlargest(5, enumerate(xs), key=lambda pair: pair[1])
result = {
    'position': 133,
    'input_token': serial['token'],
    'serial_top5': top(a),
    'batch_top5': top(b),
    'delta': {
        'different': sum(x != 0 for x in deltas), 'vocab': len(deltas),
        'max_abs': max(map(abs, deltas)),
        'relative_l2': math.sqrt(sum(x*x for x in deltas))/math.sqrt(sum(x*x for x in a)),
        'mean_abs': sum(map(abs, deltas))/len(deltas),
    },
}
(ROOT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'position': result['position'], 'input_token': result['input_token'],
                  'serial_argmax': result['serial_top5'][0][0],
                  'batch_argmax': result['batch_top5'][0][0], 'delta': result['delta']}, indent=2))
