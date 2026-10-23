#!/usr/bin/env python3
"""Pair batch GDN state rows with serial prompt controls by position/token sequence."""
import argparse
from array import array
import json
import math
from pathlib import Path
import struct

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', type=Path, required=True)
p.add_argument('--layer', type=int, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
header = struct.Struct('<8sIiqQQii')

def read(path):
    records = {}
    with path.open('rb') as f:
        while raw := f.read(header.size):
            if len(raw) != header.size:
                raise ValueError(f'{path}: truncated header')
            magic, version, layer, position, recurrent, count, token, slot = header.unpack(raw)
            data = f.read(count * 4)
            if magic != b'STGCMT1\0' or version != 1 or layer != a.layer or len(data) != count * 4:
                raise ValueError(f'{path}: invalid record at position {position}, layer {layer}')
            values = array('f'); values.frombytes(data)
            key = (slot, position)
            if key in records:
                raise ValueError(f'{path}: duplicate slot/position {key}')
            records[key] = {'position': position, 'token': token, 'recurrent': recurrent, 'values': values}
    return records

root = a.run.resolve()
serial = {control: read(root / f'serial-slot-{control}.stgcmt') for control in (0, 1)}
batch = read(root / 'batch.stgcmt')
summary = {'layer': a.layer, 'slot_mapping': {}, 'positions': []}
for batch_slot in sorted({slot for slot, _ in batch}):
    br = {pos: rec for (slot, pos), rec in batch.items() if slot == batch_slot}
    matches = {control: [pos for pos, rec in br.items()
                         if (0, pos) in serial[control] and serial[control][(0, pos)]['token'] == rec['token']]
               for control in (0, 1)}
    ranked = sorted(matches, key=lambda control: len(matches[control]), reverse=True)
    if not matches or len(matches[ranked[0]]) < 2 or (len(matches[ranked[0]]) == len(matches[ranked[1]])):
        raise ValueError(f'batch slot {batch_slot}: cannot uniquely map serial controls: '
                         f'{ {str(k): len(v) for k, v in matches.items()} }')
    control = ranked[0]
    summary['slot_mapping'][str(batch_slot)] = {
        'serial_control': control, 'matching_positions': matches[control],
        'matched_position_count': len(matches[control]),
        'compared_position_count': len(set(br) & {pos for (slot, pos) in serial[control] if slot == 0})}
    for pos in sorted(set(br) & {pos for (slot, pos) in serial[control] if slot == 0}):
        x, y = serial[control][(0, pos)], br[pos]
        if x['token'] != y['token']:
            continue
        if len(x['values']) != len(y['values']) or x['recurrent'] != y['recurrent']:
            raise ValueError(f'position {pos}: incompatible state shapes')
        delta = [u - v for u, v in zip(x['values'], y['values'])]
        recurrent_delta = delta[:x['recurrent']]
        def metric(d, ref):
            err = math.fsum(v * v for v in d)
            norm = math.fsum(v * v for v in ref)
            return {'changed_values': sum(v != 0 for v in d), 'total_values': len(d),
                    'max_abs': max(map(abs, d), default=0.0),
                    'relative_l2': math.sqrt(err / norm) if norm else 0.0}
        summary['positions'].append({'batch_slot': batch_slot, 'serial_control': control,
                                     'position': pos, 'input_token': x['token'],
                                     'whole_state': metric(delta, x['values']),
                                     'recurrent': metric(recurrent_delta, x['values'][:x['recurrent']]),
                                     'convolution': metric(delta[x['recurrent']:], x['values'][x['recurrent']:])})
for slot in summary['slot_mapping']:
    points = [r for r in summary['positions'] if str(r['batch_slot']) == slot]
    summary['slot_mapping'][slot]['first_state_difference'] = next(
        ({'position': r['position'], 'input_token': r['input_token'],
         'relative_l2': r['whole_state']['relative_l2']} for r in points if r['whole_state']['changed_values']), None)
a.output.resolve().write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'slot_mapping': summary['slot_mapping'], 'position_count': len(summary['positions'])}, indent=2))
