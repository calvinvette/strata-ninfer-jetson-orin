#!/usr/bin/env python3
"""Compare batch MoE routes and per-expert outputs with serial controls."""
import argparse
import json
import math
from pathlib import Path
import struct

HEADER = struct.Struct('<8sIIIIQqii')

def read_parts(path):
    data = path.read_bytes()
    at, records = 0, []
    while at < len(data):
        if len(data) - at < HEADER.size:
            raise ValueError(f'{path}: truncated header at {at}')
        magic, version, layer, k, reserved, width, pos, slot, token = HEADER.unpack_from(data, at)
        if magic != b'STMPART2' or version != 2 or reserved or not k or not width:
            raise ValueError(f'{path}: invalid STMPART2 header at {at}')
        count = k * width
        size = count * 4
        at += HEADER.size
        if len(data) - at < size:
            raise ValueError(f'{path}: truncated part vectors at {at}')
        parts = struct.unpack_from(f'<{count}f', data, at)
        at += size
        records.append({'layer': layer, 'k': k, 'width': width, 'position': pos,
                        'slot': slot, 'token': token, 'parts': parts})
    return records

def read_routes(path):
    lines = path.read_text().splitlines()
    if not lines:
        raise ValueError(f'{path}: empty route file')
    meta = json.loads(lines[0])
    if meta.get('format') != 'strata-verify-moe-route-v1':
        raise ValueError(f'{path}: invalid route format')
    return meta, [json.loads(line) for line in lines[1:]]

def read_outputs(path):
    data = path.read_bytes()
    at, records = 0, []
    while at < len(data):
        if len(data) - at < HEADER.size:
            raise ValueError(f'{path}: truncated output header at {at}')
        magic, version, layer, rows, reserved, width, pos, slot, token = HEADER.unpack_from(data, at)
        if magic != b'MOEOUT02' or version != 2 or rows != 1 or reserved or not width:
            raise ValueError(f'{path}: invalid MOEOUT02 header at {at}')
        at += HEADER.size
        size = width * 4
        if len(data) - at < 2 * size:
            raise ValueError(f'{path}: truncated output vectors at {at}')
        shared = struct.unpack_from(f'<{width}f', data, at)
        at += size
        combined = struct.unpack_from(f'<{width}f', data, at)
        at += size
        records.append({'layer': layer, 'position': pos, 'slot': slot, 'token': token,
                        'shared': shared, 'combined': combined})
    return records

def vector_metrics(ref, got):
    d = [x - y for x, y in zip(got, ref)]
    norm = math.sqrt(math.fsum(x * x for x in ref))
    return {'different': sum(x != y for x, y in zip(got, ref)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in d)) / max(norm, 1e-300),
            'max_abs': max((abs(x) for x in d), default=0.0)}

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', type=Path, required=True)
p.add_argument('--slot-map', type=Path, required=True,
               help='same-run JSON with slot_to_prompt mapping from committed state')
a = p.parse_args()
slot_to_prompt = json.loads(a.slot_map.read_text())['slot_to_prompt']
serial_parts = [read_parts(a.run / f'serial-slot-{i}.parts') for i in (0, 1)]
batch_parts = read_parts(a.run / 'batch.parts')
serial_routes = [read_routes(a.run / f'serial-slot-{i}.routes.jsonl')[1] for i in (0, 1)]
batch_routes = read_routes(a.run / 'batch.routes.jsonl')[1]
serial_outputs = [read_outputs(a.run / f'serial-slot-{i}.stmoe') for i in (0, 1)]
batch_outputs = read_outputs(a.run / 'batch.stmoe')
route_map = [{(r['position'], r['token_id']): r for r in rows} for rows in serial_routes]
parts_map = [{(r['position'], r['token']): r for r in rows} for rows in serial_parts]
output_map = [{(r['position'], r['token']): r for r in rows} for rows in serial_outputs]
batch_route_map = {(r['position'], r['token_id'], r.get('slot', -1)): r for r in batch_routes}
batch_output_map = {(r['position'], r['token'], r['slot']): r for r in batch_outputs}
results = []
for b in batch_parts:
    if b['slot'] < 0:
        continue
    prompt = int(slot_to_prompt[str(b['slot'])])
    key = (b['position'], b['token'])
    ref_parts = parts_map[prompt].get(key)
    ref_route = route_map[prompt].get(key)
    got_route = batch_route_map.get((b['position'], b['token'], b['slot']))
    ref_output = output_map[prompt].get(key)
    got_output = batch_output_map.get((b['position'], b['token'], b['slot']))
    if ref_parts is None or ref_route is None or got_route is None or ref_output is None or got_output is None:
        raise ValueError(f'no matching serial/batch route and parts record for slot={b["slot"]}, pos={b["position"]}')
    if b['k'] != ref_parts['k'] or b['width'] != ref_parts['width']:
        raise ValueError('serial/batch expert part dimensions differ')
    ranks = []
    for rank in range(b['k']):
        beg, end = rank * b['width'], (rank + 1) * b['width']
        ranks.append({'rank': rank, 'expert_id': got_route['ids'][rank],
                      'route_id_matches': got_route['ids'][rank] == ref_route['ids'][rank],
                      'weight_abs_delta': abs(got_route['weights'][rank] - ref_route['weights'][rank]),
                      'part': vector_metrics(ref_parts['parts'][beg:end], b['parts'][beg:end])})
    predicted = [0.0] * b['width']
    for rank in range(b['k']):
        beg, end = rank * b['width'], (rank + 1) * b['width']
        old_weight, new_weight = ref_route['weights'][rank], got_route['weights'][rank]
        for i, (old_part, new_part) in enumerate(zip(ref_parts['parts'][beg:end], b['parts'][beg:end])):
            predicted[i] += new_weight * new_part - old_weight * old_part
    actual = [new - old for old, new in zip(ref_output['combined'], got_output['combined'])]
    residual = [new - old for old, new in zip(actual, predicted)]
    results.append({'position': b['position'], 'token': b['token'], 'slot': b['slot'],
                    'serial_prompt': prompt, 'route_ids_exact': got_route['ids'] == ref_route['ids'],
                    'route_weights': vector_metrics(ref_route['weights'], got_route['weights']),
                    'combined_output_delta': vector_metrics(ref_output['combined'], got_output['combined']),
                    'weighted_parts_prediction_delta': vector_metrics(ref_output['combined'],
                                                                       [x + y for x, y in zip(ref_output['combined'], predicted)]),
                    'prediction_residual': vector_metrics(actual, predicted),
                    'rank_outputs': ranks})
print(json.dumps({'records': results}, indent=2))
