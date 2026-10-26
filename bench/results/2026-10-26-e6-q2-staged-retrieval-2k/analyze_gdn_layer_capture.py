#!/usr/bin/env python3
"""Compare paired STGDIAG4 GDN intermediate captures by token position."""
from __future__ import annotations

import argparse
import array
import json
import math
from pathlib import Path
import struct
import sys


HEADER = struct.Struct('<8sIiiqQQQQQ8i')


def read_capture(path: Path, expected_layer: int) -> dict[int, dict]:
    raw = path.read_bytes()
    offset = 0
    records: dict[int, dict] = {}
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f'{path}: truncated header at byte {offset}')
        values = HEADER.unpack_from(raw, offset)
        magic, version, layer, rows, pos0, n, c, hv, zv, state_floats, *tokens = values
        if magic != b'STGDIAG4' or version != 4 or layer != expected_layer or not 1 <= rows <= len(tokens):
            raise ValueError(f'{path}: unsupported header at byte {offset}: {values[:5]}')
        dimensions = {'x': n, 'qkv': c, 'h': c, 'gate': hv, 'beta': hv,
                      'z': zv, 'y': zv, 'gdn_out': n, 'ffn_x': n, 'ffn_y': n}
        cursor = offset + HEADER.size
        fields: dict[str, tuple[array.array, int]] = {}
        for name, width in dimensions.items():
            values_f = array.array('f')
            end = cursor + rows * width * 4
            if end > len(raw):
                raise ValueError(f'{path}: truncated {name} payload at byte {cursor}')
            values_f.frombytes(raw[cursor:end])
            if sys.byteorder != 'little':
                values_f.byteswap()
            fields[name] = (values_f, width)
            cursor = end
        for row in range(rows):
            position = pos0 + row
            if position in records:
                raise ValueError(f'{path}: duplicate position {position}')
            records[position] = {
                'token': tokens[row],
                'fields': {name: values_f[row * width:(row + 1) * width]
                           for name, (values_f, width) in fields.items()},
                'metadata': {'layer': layer, 'n_embd': n, 'conv_channels': c,
                             'v_heads': hv, 'value_dim': zv, 'state_floats': state_floats},
            }
        offset = cursor
    if not records:
        raise ValueError(f'{path}: no captures')
    return records


def compare(left: array.array, right: array.array) -> dict:
    delta = [float(a) - float(b) for a, b in zip(left, right)]
    norm = math.sqrt(math.fsum(float(value) ** 2 for value in right))
    delta_norm = math.sqrt(math.fsum(value * value for value in delta))
    return {'exact': all(a == b for a, b in zip(left, right)),
            'different': sum(a != b for a, b in zip(left, right)),
            'relative_l2': delta_norm / norm if norm else 0.0,
            'max_abs': max(map(abs, delta), default=0.0)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='directory containing <arm>.layerN.gdn-diag')
    parser.add_argument('--layer', type=int, required=True)
    parser.add_argument('--reference', default='cpu-miss')
    parser.add_argument('--candidate', default='ninfer-staged')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    left = read_capture(args.root / f'{args.reference}.layer{args.layer}.gdn-diag', args.layer)
    right = read_capture(args.root / f'{args.candidate}.layer{args.layer}.gdn-diag', args.layer)
    if left.keys() != right.keys():
        raise ValueError(f'captured positions differ: {sorted(left)} vs {sorted(right)}')
    result = {'schema': 1, 'layer': args.layer, 'positions': []}
    for position in sorted(left):
        a, b = left[position], right[position]
        if a['token'] != b['token'] or a['metadata'] != b['metadata']:
            raise ValueError(f'position {position}: token or tensor geometry differs')
        result['positions'].append({
            'position': position,
            'token_id': a['token'],
            'stages': [{'field': name, **compare(a['fields'][name], b['fields'][name])}
                       for name in a['fields']],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'layer': args.layer, 'positions': [row['position'] for row in result['positions']]}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
