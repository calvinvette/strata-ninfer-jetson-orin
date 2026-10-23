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
p.add_argument('--layer', required=True,
               help='GDN model layer number or all for every captured layer')
p.add_argument('--batch-slot', type=int, help='restrict analysis to an internal batch slot')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
header = struct.Struct('<8sIiqQQii')
expected_layer = None if a.layer == 'all' else int(a.layer)

def read(path):
    records = {}
    with path.open('rb') as f:
        while raw := f.read(header.size):
            if len(raw) != header.size:
                raise ValueError(f'{path}: truncated header')
            magic, version, layer, position, recurrent, count, token, slot = header.unpack(raw)
            data = f.read(count * 4)
            if magic != b'STGCMT1\0' or version != 1 or (expected_layer is not None and layer != expected_layer) or len(data) != count * 4:
                raise ValueError(f'{path}: invalid record at position {position}, layer {layer}')
            values = array('f'); values.frombytes(data)
            key = (slot, layer, position)
            if key in records:
                raise ValueError(f'{path}: duplicate slot/position {key}')
            records[key] = {'layer': layer, 'position': position, 'token': token,
                            'recurrent': recurrent, 'values': values}
    return records

root = a.run.resolve()
serial = {control: read(root / f'serial-slot-{control}.stgcmt') for control in (0, 1)
          if (root / f'serial-slot-{control}.stgcmt').is_file()}
if not serial and (root / 'serial.stgcmt').is_file():
    serial['single'] = read(root / 'serial.stgcmt')
batch = read(root / 'batch.stgcmt')
if a.batch_slot is not None:
    batch = {key: value for key, value in batch.items() if key[0] == a.batch_slot}
summary = {'layer': a.layer if expected_layer is None else expected_layer,
           'slot_mapping': {}, 'positions': []}
for batch_slot in sorted({slot for slot, _, _ in batch}):
    br = {(layer, pos): rec for (slot, layer, pos), rec in batch.items() if slot == batch_slot}
    matches = {control: sorted({pos for (layer, pos), rec in br.items()
                                if (0, layer, pos) in serial[control] and
                                serial[control][(0, layer, pos)]['token'] == rec['token']})
               for control in serial}
    ranked = sorted(matches, key=lambda control: len(matches[control]), reverse=True)
    minimum_positions = 1 if expected_layer is None else 2
    if (not matches or len(matches[ranked[0]]) < minimum_positions or
            (len(ranked) > 1 and len(matches[ranked[0]]) == len(matches[ranked[1]]))):
        raise ValueError(f'batch slot {batch_slot}: cannot uniquely map serial controls: '
                         f'{ {str(k): len(v) for k, v in matches.items()} }')
    control = ranked[0]
    summary['slot_mapping'][str(batch_slot)] = {
        'serial_control': control, 'matching_positions': matches[control],
        'matched_position_count': len(matches[control]),
        'compared_position_count': len({pos for (layer, pos), rec in br.items()
                                        if (0, layer, pos) in serial[control] and
                                        serial[control][(0, layer, pos)]['token'] == rec['token']}),
        'compared_state_record_count': sum(1 for (layer, pos), rec in br.items()
                                           if (0, layer, pos) in serial[control] and
                                           serial[control][(0, layer, pos)]['token'] == rec['token'])}
    for layer, pos in sorted(br):
        y = br[(layer, pos)]
        if (0, layer, pos) not in serial[control]:
            continue
        x = serial[control][(0, layer, pos)]
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
        summary['positions'].append({'batch_slot': batch_slot, 'serial_control': control, 'layer': layer,
                                     'position': pos, 'input_token': x['token'],
                                     'whole_state': metric(delta, x['values']),
                                     'recurrent': metric(recurrent_delta, x['values'][:x['recurrent']]),
                                     'convolution': metric(delta[x['recurrent']:], x['values'][x['recurrent']:])})
for slot in summary['slot_mapping']:
    points = sorted((r for r in summary['positions'] if str(r['batch_slot']) == slot),
                    key=lambda r: (r['position'], r['layer']))
    summary['slot_mapping'][slot]['first_state_difference'] = next(
        ({'layer': r['layer'], 'position': r['position'], 'input_token': r['input_token'],
         'relative_l2': r['whole_state']['relative_l2']} for r in points if r['whole_state']['changed_values']), None)
a.output.resolve().write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'slot_mapping': summary['slot_mapping'], 'position_count': len(summary['positions'])}, indent=2))
