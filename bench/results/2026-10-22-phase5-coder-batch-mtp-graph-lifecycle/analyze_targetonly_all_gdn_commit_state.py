#!/usr/bin/env python3
"""Compare serial and batch committed GDN states at one exact token boundary."""
import argparse
import json
import math
from pathlib import Path
import struct

HEADER = struct.Struct('<8sIiqQQii')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--serial', type=Path, required=True)
parser.add_argument('--batch', type=Path, required=True)
parser.add_argument('--position', type=int, default=119)
parser.add_argument('--token', type=int, default=16)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()

def read_records(path):
    data, at, records = path.read_bytes(), 0, []
    while at < len(data):
        if len(data) - at < HEADER.size:
            raise ValueError(f'{path}: truncated header at {at}')
        magic, version, layer, position, recurrent, count, token, slot = HEADER.unpack_from(data, at)
        at += HEADER.size
        if magic[:7] != b'STGCMT1' or version != 1 or recurrent > count or count == 0:
            raise ValueError(f'{path}: invalid record header at {at - HEADER.size}')
        size = count * 4
        if len(data) - at < size:
            raise ValueError(f'{path}: truncated state payload at {at}')
        values = struct.unpack_from(f'<{count}f', data, at)
        at += size
        records.append({'layer': layer, 'position': position, 'token': token, 'slot': slot,
                        'recurrent': recurrent, 'values': values})
    return records

def compare(reference, actual):
    if len(reference) != len(actual):
        raise ValueError('state vector lengths differ')
    diffs = [b - a for a, b in zip(reference, actual)]
    norm = math.sqrt(math.fsum(float(a) * a for a in reference))
    return {'values': len(reference), 'different_values': sum(a != b for a, b in zip(reference, actual)),
            'max_abs': max(map(abs, diffs), default=0.0),
            'relative_l2': math.sqrt(math.fsum(float(d) * d for d in diffs)) / norm if norm else 0.0}

def select(path, label):
    records = [r for r in read_records(path)
               if r['position'] == args.position and r['token'] == args.token]
    if any(r['slot'] != 0 for r in records):
        raise ValueError(f'{label}: expected physical slot 0 in every record')
    selected = {r['layer']: r for r in records}
    if len(selected) != len(records):
        raise ValueError(f'{label}: duplicate layer records')
    return selected

serial = select(args.serial, 'serial')
batch = select(args.batch, 'batch')
if not serial or serial.keys() != batch.keys():
    raise ValueError(f'missing/unpaired layer records: serial={sorted(serial)}, batch={sorted(batch)}')
if any(serial[layer]['recurrent'] != batch[layer]['recurrent'] or
       len(serial[layer]['values']) != len(batch[layer]['values']) for layer in serial):
    raise ValueError('serial and batch state dimensions differ')
if len(serial) != 36:
    raise ValueError(f'expected the 36 GDN layers, got {len(serial)}')

layers = []
aggregate_changed = aggregate_values = 0
aggregate_error_sq = aggregate_reference_sq = 0.0
aggregate_max_abs = 0.0
for layer in sorted(serial):
    s, b = serial[layer], batch[layer]
    recurrent = s['recurrent']
    for a, actual in zip(s['values'], b['values']):
        delta = float(actual) - float(a)
        aggregate_changed += delta != 0.0
        aggregate_values += 1
        aggregate_error_sq += delta * delta
        aggregate_reference_sq += float(a) * float(a)
        aggregate_max_abs = max(aggregate_max_abs, abs(delta))
    layers.append({'layer': layer,
                   'recurrent': compare(s['values'][:recurrent], b['values'][:recurrent]),
                   'convolution': compare(s['values'][recurrent:], b['values'][recurrent:]),
                   'combined': compare(s['values'], b['values'])})
first = next((x['layer'] for x in layers if x['combined']['different_values']), None)
result = {'schema': 1, 'position': args.position, 'token': args.token, 'batch_slot': 0,
          'layers_compared': len(layers), 'first_changed_layer': first,
          'all_layer_state': {'values': aggregate_values, 'different_values': aggregate_changed,
                              'max_abs': aggregate_max_abs,
                              'relative_l2': math.sqrt(aggregate_error_sq / aggregate_reference_sq)
                                             if aggregate_reference_sq else 0.0},
          'layers': layers}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
