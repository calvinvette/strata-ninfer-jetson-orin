#!/usr/bin/env python3
"""Compare serial and delayed one-row batch MoE route/parts/output at layer 11."""
import argparse
import json
import math
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--layer', type=int, default=11)
parser.add_argument('--position', type=int, default=119)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
HEADER = struct.Struct('<8sIIIIQqii')

def records(path, magic, kind):
    data, at, out = path.read_bytes(), 0, []
    while at < len(data):
        if len(data) - at < HEADER.size:
            raise ValueError(f'{path}: truncated {kind} header at {at}')
        got_magic, version, layer, count, reserved, width, pos, slot, token = HEADER.unpack_from(data, at)
        if got_magic != magic or version != 2 or reserved or layer != args.layer or count < 1 or (kind == 'output' and count != 1):
            raise ValueError(f'{path}: invalid {kind} record at {at}')
        at += HEADER.size
        n = width * count
        arrays = 2 if kind == 'output' else 1
        size = n * arrays * 4
        if len(data) - at < size:
            raise ValueError(f'{path}: truncated {kind} payload at {at}')
        first = struct.unpack_from(f'<{n}f', data, at)
        at += n * 4
        second = struct.unpack_from(f'<{n}f', data, at) if arrays == 2 else None
        if second is not None:
            at += n * 4
        out.append({'position': pos, 'slot': slot, 'token': token, 'width': width,
                    'first': first, 'second': second})
    return out

def route_records(path):
    lines = path.read_text().splitlines()
    if not lines or json.loads(lines[0]).get('format') != 'strata-verify-moe-route-v1':
        raise ValueError(f'{path}: invalid route file')
    return [json.loads(line) for line in lines[1:]]

def metrics(ref, got):
    delta = [b - a for a, b in zip(ref, got)]
    denom = math.sqrt(math.fsum(a*a for a in ref))
    return {'different': sum(a != b for a, b in zip(ref, got)),
            'max_abs': max(map(abs, delta), default=0.0),
            'relative_l2': math.sqrt(math.fsum(d*d for d in delta)) / denom if denom else 0.0}

def dispatch_rows(path):
    lines = path.read_text().splitlines()
    if not lines or json.loads(lines[0]).get('format') != 'strata-moe-dispatch-v3':
        raise ValueError(f'{path}: invalid owner-dispatch capture')
    return [json.loads(line) for line in lines[1:]]

serial_parts = records(args.run / 'moe-parts.stmparts', b'STMPART2', 'parts')
batch_parts = [r for r in serial_parts if r['slot'] == 0 and r['position'] == args.position]
serial_parts = [r for r in serial_parts if r['slot'] < 0 and r['position'] == args.position]
serial_outputs = records(args.run / 'moe-output.stmoe', b'MOEOUT02', 'output')
batch_outputs = [r for r in serial_outputs if r['slot'] == 0 and r['position'] == args.position]
serial_outputs = [r for r in serial_outputs if r['slot'] < 0 and r['position'] == args.position]
routes = route_records(args.run / 'moe-routes.jsonl')
batch_routes = [r for r in routes if r.get('layer') == args.layer and r.get('slot') == 0 and r['position'] == args.position]
serial_routes = [r for r in routes if r.get('layer') == args.layer and r.get('slot', -1) < 0 and r['position'] == args.position]
groups = (serial_parts, batch_parts, serial_outputs, batch_outputs, serial_routes, batch_routes)
if any(len(group) != 1 for group in groups):
    raise ValueError('expected one matched serial and slot-0 batch route, parts, and output row; counts=' +
                     repr([len(group) for group in groups]))
sp, bp = serial_parts[0], batch_parts[0]
so, bo = serial_outputs[0], batch_outputs[0]
sr, br = serial_routes[0], batch_routes[0]
if not (sp['token'] == bp['token'] == so['token'] == bo['token'] == sr['token_id'] == br['token_id']):
    raise ValueError('route/parts/output rows do not share the same token')
if sp['width'] != bp['width'] or len(sp['first']) != len(bp['first']):
    raise ValueError('serial and batch expert-part dimensions differ')
rank_metrics = []
k = len(br['ids'])
width = len(bp['first']) // k
predicted = [0.0] * width
for rank in range(k):
    start, end = rank * width, (rank + 1) * width
    rank_metrics.append({'rank': rank, 'serial_expert': sr['ids'][rank], 'batch_expert': br['ids'][rank],
                         'route_id_matches': sr['ids'][rank] == br['ids'][rank],
                         'weight_abs_delta': abs(sr['weights'][rank] - br['weights'][rank]),
                         'expert_part': metrics(sp['first'][start:end], bp['first'][start:end])})
    for i in range(width):
        predicted[i] += br['weights'][rank] * bp['first'][start + i] - sr['weights'][rank] * sp['first'][start + i]
combined_delta = [b - a for a, b in zip(so['second'], bo['second'])]
result = {'layer': args.layer, 'position': args.position, 'token': bp['token'], 'batch_slot': 0,
          'route_ids_exact': sr['ids'] == br['ids'],
          'route_weights': metrics(sr['weights'], br['weights']),
          'shared_output': metrics(so['first'], bo['first']),
          'combined_output': metrics(so['second'], bo['second']),
          'weighted_expert_parts_delta': {'l2': math.sqrt(math.fsum(x*x for x in predicted)),
                                          'max_abs': max(map(abs, predicted), default=0.0)},
          'combined_output_delta_l2': math.sqrt(math.fsum(x*x for x in combined_delta)),
          'combined_delta_explained_residual': metrics(predicted, combined_delta),
          'rank_outputs': rank_metrics}
serial_owner_rows = [r for r in dispatch_rows(args.run / 'serial.moe-owners.jsonl')
                     if r['layer'] == args.layer and r['position'] == args.position and r['token_id'] == bp['token']]
batch_owner_rows = [r for r in dispatch_rows(args.run / 'batch.moe-owners.jsonl')
                    if r['layer'] == args.layer and r['position'] == args.position and r['token_id'] == bp['token']]
if len(serial_owner_rows) == len(batch_owner_rows) == 1:
    serial_owner, batch_owner = serial_owner_rows[0], batch_owner_rows[0]
    owner_labels = {'-1': 'CPU', '0': 'primary VRAM', '1': 'PCIe', '2': 'peer/helper GPU'}
    result['owner_codes'] = owner_labels
    result['owner_changes'] = [
        {'rank': rank, 'expert': br['ids'][rank],
         'serial_owner': owner_labels.get(str(serial_owner['route_kind'][rank]), 'unknown'),
         'batch_owner': owner_labels.get(str(batch_owner['route_kind'][rank]), 'unknown')}
        for rank in range(k) if serial_owner['route_kind'][rank] != batch_owner['route_kind'][rank]]
    result['owner_capture_activation_valid'] = {
        'serial': serial_owner['activation_valid'], 'batch': batch_owner['activation_valid']}
    if serial_owner['activation_valid'] and batch_owner['activation_valid']:
        result['moe_input_activation'] = metrics(serial_owner['activation'], batch_owner['activation'])
else:
    raise ValueError(f'expected one serial and one batch dispatch owner row; '
                     f'found serial={len(serial_owner_rows)}, batch={len(batch_owner_rows)}')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
