#!/usr/bin/env python3
"""Compare STMOEOUT2 shared and combined outputs with fresh serial controls."""
import argparse
import json
import math
from pathlib import Path
import struct

HEADER = struct.Struct('<8sIIIIQqii')

def read(path):
    data = path.read_bytes()
    at, records = 0, []
    while at < len(data):
        if len(data) - at < HEADER.size:
            raise ValueError(f'{path}: truncated header at {at}')
        magic, version, layer, rows, reserved, width, pos, slot, token = HEADER.unpack_from(data, at)
        at += HEADER.size
        if magic != b'MOEOUT02' or version != 2 or rows != 1 or reserved or width != 2560:
            raise ValueError(f'{path}: invalid header {magic!r}, v{version}, rows={rows}, width={width}')
        nbytes = width * 4
        if len(data) - at < nbytes * 2:
            raise ValueError(f'{path}: truncated arrays at {at}')
        shared = struct.unpack_from(f'<{width}f', data, at)
        at += nbytes
        combined = struct.unpack_from(f'<{width}f', data, at)
        at += nbytes
        records.append({'layer': layer, 'position': pos, 'slot': slot, 'token': token,
                        'shared': shared, 'combined': combined})
    return records

def metrics(ref, got):
    d = [x - y for x, y in zip(got, ref)]
    denom = math.sqrt(math.fsum(x * x for x in ref))
    return {'different': sum(x != y for x, y in zip(got, ref)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in d)) / denom if denom else None,
            'max_abs': max((abs(x) for x in d), default=0.0)}

p = argparse.ArgumentParser()
p.add_argument('--run', type=Path, required=True)
p.add_argument('--slot-map', type=Path, required=True,
               help='compact JSON with slot_to_prompt mapping established from the same run')
a = p.parse_args()
batch = read(a.run / 'batch.stmoe')
serial = {name: read(a.run / f'serial-{name}.stmoe') for name in ('slot-0', 'slot-1')}
mapping = json.loads(a.slot_map.read_text())['slot_to_prompt']
out = []
for rec in batch:
    if rec['slot'] < 0:
        continue
    controls = []
    # This short pair has identical consumed tokens. Map batch slots from the
    # same run's recurrent-state capture in the companion summary.
    name = f"slot-{mapping[str(rec['slot'])]}"
    ref = next((x for x in serial[name] if x['position'] == rec['position'] and x['token'] == rec['token']), None)
    if ref is None:
        raise ValueError(f"no serial row for {name} at {rec['position']} token {rec['token']}")
    out.append({'slot': rec['slot'], 'control': name, 'position': rec['position'], 'token': rec['token'],
                'shared': metrics(ref['shared'], rec['shared']),
                'combined': metrics(ref['combined'], rec['combined'])})
print(json.dumps({'layer': batch[0]['layer'] if batch else None, 'records': out}, indent=2))
