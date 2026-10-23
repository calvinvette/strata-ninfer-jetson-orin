#!/usr/bin/env python3
"""Compare serial and batch slot-1 committed GDN state at a selected position."""
import argparse
from array import array
import json
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', type=Path, default=Path(__file__).resolve().parent/'position-133-state')
parser.add_argument('--position', type=int, default=133)
parser.add_argument('--output', type=Path, help='analysis JSON path; defaults to <run>/analysis.json')
parser.add_argument('--batch-slot', type=int, default=1,
                    help='verifier row containing the target service request (internal slots can be reassigned)')
args = parser.parse_args()
ROOT = args.run.resolve()
POSITION = args.position
HEADER = struct.Struct('<8sIiqQQii')

def records(path, wanted_slot):
    out = {}
    with path.open('rb') as f:
        while raw := f.read(HEADER.size):
            if len(raw) != HEADER.size:
                raise ValueError(f'{path}: truncated header')
            magic, version, layer, position, recurrent, count, token, slot = HEADER.unpack(raw)
            if magic != b'STGCMT1\0' or version != 1:
                raise ValueError(f'{path}: unexpected record')
            payload = f.read(count*4)
            if len(payload) != count*4:
                raise ValueError(f'{path}: truncated payload')
            if position == POSITION and slot == wanted_slot:
                values = array('f'); values.frombytes(payload)
                out[layer] = {'position': position, 'token': token,
                              'recurrent': recurrent, 'values': values}
    return out

serial_slot_path = ROOT/f'serial-slot-{args.batch_slot}.stgcmt'
if not serial_slot_path.is_file():
    serial_slot_path = ROOT/'serial.stgcmt'
serial = records(serial_slot_path, 0)
batch = records(ROOT/'batch.stgcmt', args.batch_slot)
if not serial or set(serial) != set(batch):
    raise ValueError(f'layer mismatch: serial={sorted(serial)} batch={sorted(batch)}')
rows = []
for layer in sorted(serial):
    a, b = serial[layer], batch[layer]
    if a['token'] != b['token']:
        raise ValueError(f'layer {layer}: input token differs {a["token"]} vs {b["token"]}')
    delta = [x-y for x,y in zip(a['values'], b['values'])]
    def metrics(start, end):
        ds = delta[start:end]
        av = a['values'][start:end]
        changed = sum(x != 0 for x in ds)
        sum_sq = sum(x*x for x in ds)
        norm_sq = sum(x*x for x in av)
        return {'changed_values': changed, 'total_values': len(ds),
                'max_abs': max(map(abs, ds), default=0.0),
                'relative_l2': (sum_sq/norm_sq)**0.5 if norm_sq else 0.0}
    rows.append({'layer': layer, 'input_token': a['token'],
                 'whole_state': metrics(0, len(delta)),
                 'recurrent': metrics(0, a['recurrent']),
                 'convolution': metrics(a['recurrent'], len(delta))})
result = {'position': POSITION, 'serial_layers': sorted(serial), 'batch_slot': args.batch_slot,
          'first_changed_layer': next((x['layer'] for x in rows if x['whole_state']['changed_values']), None),
          'comparisons': rows,
          'limits': ['GDN committed-state capture only; other activations and state families are not covered.',
                     'This is one diagnostic cell and does not identify an upstream arithmetic cause.']}
output = args.output.resolve() if args.output else ROOT/'analysis.json'
output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'position': POSITION, 'first_changed_layer': result['first_changed_layer'],
                  'changed_layers': [x['layer'] for x in rows if x['whole_state']['changed_values']],
                  'records': len(rows)}, indent=2))
