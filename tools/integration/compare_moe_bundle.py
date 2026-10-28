#!/usr/bin/env python3
"""Compare concatenated STMOEBN1 multi-layer MoE diagnostic records."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct

HEADER = struct.Struct('<8sIIIIQqii')


def read_bundle(path: Path) -> dict[tuple[int, int], tuple[dict, dict[str, tuple]]]:
    raw = path.read_bytes()
    records = {}
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f'{path}: truncated STMOEBN1 header')
        magic, version, layer, k, reserved, n_embd, position, slot, token = HEADER.unpack_from(raw, offset)
        if magic != b'STMOEBN1' or version != 1 or reserved != 0 or k == 0 or n_embd == 0:
            raise ValueError(f'{path}: invalid STMOEBN1 header at byte {offset}')
        dims = {'route_ids': k, 'route_weights': k, 'input': n_embd,
                'expert_parts': k * n_embd, 'shared_output': n_embd, 'combined_output': n_embd}
        payload_bytes = sum(dims.values()) * 4
        record_bytes = HEADER.size + payload_bytes
        if len(raw) - offset < record_bytes:
            raise ValueError(f'{path}: truncated STMOEBN1 payload at byte {offset}')
        values = {}
        cursor = offset + HEADER.size
        for name, count in dims.items():
            fmt = f'<{count}i' if name == 'route_ids' else f'<{count}f'
            values[name] = struct.unpack_from(fmt, raw, cursor)
            cursor += count * 4
        key = (layer, position)
        if key in records:
            raise ValueError(f'{path}: duplicate MoE bundle record for layer {layer}, position {position}')
        records[key] = ({'version': version, 'layer': layer, 'k': k, 'n_embd': n_embd,
                         'position': position, 'slot': slot, 'token': token}, values)
        offset += record_bytes
    if not records:
        raise ValueError(f'{path}: empty MoE bundle')
    return records


def metrics(a: tuple, b: tuple) -> dict:
    if len(a) != len(b):
        raise ValueError('MoE bundle field dimensions differ')
    diff2 = math.fsum((float(y) - float(x)) ** 2 for x, y in zip(a, b))
    ref2 = math.fsum(float(x) ** 2 for x in a)
    return {'count': len(a), 'different': sum(x != y for x, y in zip(a, b)),
            'relative_l2': math.sqrt(diff2 / ref2) if ref2 else 0.0,
            'max_abs': max((abs(float(y) - float(x)) for x, y in zip(a, b)), default=0.0)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ref = read_bundle(args.reference)
    cand = read_bundle(args.candidate)
    if set(ref) != set(cand):
        raise SystemExit('MoE bundle layer/position records differ')
    result = {'schema': 1, 'format': 'STMOEBN1', 'records': []}
    for key in sorted(ref):
        rh, rv = ref[key]
        ch, cv = cand[key]
        if (rh['k'], rh['n_embd'], rh['slot'], rh['token']) != (ch['k'], ch['n_embd'], ch['slot'], ch['token']):
            raise SystemExit(f'incompatible MoE bundle headers at layer {key[0]}, position {key[1]}')
        fields = {name: metrics(rv[name], cv[name]) for name in rv}
        result['records'].append({'header': rh, 'fields': fields})
    result['first_differing_layer'] = next(
        (record['header']['layer'] for record in result['records']
         if any(metric['different'] for metric in record['fields'].values())), None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
