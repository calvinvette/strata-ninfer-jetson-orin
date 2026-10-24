#!/usr/bin/env python3
"""Pair captured routed-expert parts with native CPU/GPU oracle outputs."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

H = struct.Struct('<8sIIIIQqii')

def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def owner(path, layer, position, token, expert):
    found = [r for r in rows(path) if r.get('layer') == layer and r.get('position') == position
             and r.get('token_id') == token and expert in r.get('ids', [])]
    if len(found) != 1:
        raise ValueError(f'{path}: expected one matching owner row, got {len(found)}')
    return found[0]

def route(path, layer, position, token):
    found = [r for r in rows(path) if r.get('layer') == layer and r.get('position') == position
             and r.get('token_id') == token]
    if len(found) != 1:
        raise ValueError(f'{path}: expected one matching route row, got {len(found)}')
    return found[0]

def part(path, layer, position, token, rank):
    data = path.read_bytes(); off = 0
    found = []
    while off < len(data):
        if len(data) - off < H.size:
            raise ValueError(f'{path}: truncated header')
        magic, version, l, k, reserved, width, pos, slot, tok = H.unpack_from(data, off)
        off += H.size
        if magic != b'STMPART2' or version != 2 or reserved:
            raise ValueError(f'{path}: unsupported STMPART2 record')
        n = k * width * 4
        if len(data) - off < n:
            raise ValueError(f'{path}: truncated payload')
        payload = data[off:off+n]; off += n
        if l == layer and pos == position and tok == token:
            if rank >= k:
                raise ValueError(f'{path}: rank outside part array')
            found.append((width, slot, payload[rank*width*4:(rank+1)*width*4]))
    if len(found) != 1:
        raise ValueError(f'{path}: expected one matching part record, got {len(found)}')
    return found[0]

def compare(a, b):
    if len(a) != len(b) or len(a) % 4:
        raise ValueError('float payload size mismatch')
    x = struct.unpack(f'<{len(a)//4}f', a)
    y = struct.unpack(f'<{len(b)//4}f', b)
    d = [u-v for u,v in zip(x,y)]
    den = math.fsum(v*v for v in x)
    return {'values': len(x), 'different_values': sum(u != v for u,v in zip(x,y)),
            'max_abs': max(map(abs,d), default=0.0),
            'relative_l2': math.sqrt(math.fsum(v*v for v in d)/den) if den else 0.0}

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', type=Path, required=True)
p.add_argument('--oracle-dir', type=Path, required=True)
p.add_argument('--layer', type=int, required=True)
p.add_argument('--position', type=int, required=True)
p.add_argument('--token', type=int, required=True)
p.add_argument('--expert', type=int, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
serial = owner(a.run/'serial-slot-1.owners.jsonl', a.layer, a.position, a.token, a.expert)
batch = owner(a.run/'batch.owners.jsonl', a.layer, a.position, a.token, a.expert)
serial_route = route(a.run/'serial-slot-1.routes.jsonl', a.layer, a.position, a.token)
batch_route = route(a.run/'batch.routes.jsonl', a.layer, a.position, a.token)
if serial['ids'] != batch['ids'] or serial_route['ids'] != batch_route['ids'] or serial_route['weights'] != batch_route['weights']:
    raise ValueError('serial/batch route differs; owner arithmetic comparison is unsupported')
act_s = struct.pack(f'<{len(serial["activation"])}f', *serial['activation'])
act_b = struct.pack(f'<{len(batch["activation"])}f', *batch['activation'])
if act_s != act_b:
    raise ValueError('serial/batch activation differs; owner arithmetic comparison is unsupported')
rank = serial['ids'].index(a.expert)
if rank != batch['ids'].index(a.expert):
    raise ValueError('expert route rank mismatch')
width_s, slot_s, service_s = part(a.run/'serial-slot-1.parts.stmparts', a.layer, a.position, a.token, rank)
width_b, slot_b, service_b = part(a.run/'batch.parts.stmparts', a.layer, a.position, a.token, rank)
if width_s != width_b:
    raise ValueError('service part widths differ')
oracle_cpu = (a.oracle_dir/f'layer-{a.layer}-expert-{a.expert}-cpu-output.f32').read_bytes()
oracle_gpu = (a.oracle_dir/f'layer-{a.layer}-expert-{a.expert}-gpu-output.f32').read_bytes()
if len(oracle_cpu) != width_s*4 or len(oracle_gpu) != width_s*4:
    raise ValueError('oracle and service part dimensions differ')
result = {
    'scope': 'one exact-activation, exact-route selected-expert owner comparison',
    'layer': a.layer, 'position': a.position, 'input_token': a.token,
    'expert': a.expert, 'rank': rank, 'route_ids': serial['ids'],
    'route_weights': serial_route['weights'],
    'owner_codes': {'serial': serial['route_kind'][rank], 'batch': batch['route_kind'][rank]},
    'activation_sha256': hashlib.sha256(act_s).hexdigest(),
    'service_rows': {'serial': {'row': serial['row'], 'stream_row': serial['stream_row'], 'n_tok': serial['n_tok']},
                     'batch': {'row': batch['row'], 'stream_row': batch['stream_row'], 'n_tok': batch['n_tok']}},
    'serial_service_matches_gpu_oracle_bitwise': service_s == oracle_gpu,
    'batch_service_matches_cpu_oracle_bitwise': service_b == oracle_cpu,
    'serial_service_vs_gpu_oracle': compare(service_s, oracle_gpu),
    'batch_service_vs_cpu_oracle': compare(service_b, oracle_cpu),
    'cpu_vs_gpu_oracle': compare(oracle_gpu, oracle_cpu),
    'limits': ['One model/layer/expert/activation only; no general owner-parity claim.',
               'This operator check does not establish token quality or long-run state behavior.']}
a.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: result[k] for k in ('layer','position','input_token','expert','rank','owner_codes',
      'serial_service_matches_gpu_oracle_bitwise','batch_service_matches_cpu_oracle_bitwise','cpu_vs_gpu_oracle')}, indent=2))
