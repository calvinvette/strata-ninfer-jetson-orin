#!/usr/bin/env python3
"""Compare STGDIAG4 GDN layer rows and optional STGDOO1 raw outputs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct

DIAG_HEADER = struct.Struct('<8sIiiqQQQQQ8i')
O_HEADER = struct.Struct('<8sIiiqQ8i')
FIELD_NAMES = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')


def metrics(a: tuple[float, ...], b: tuple[float, ...]) -> dict:
    if len(a) != len(b):
        raise ValueError('diagnostic field dimensions differ')
    diff2 = math.fsum((float(y) - float(x)) ** 2 for x, y in zip(a, b))
    ref2 = math.fsum(float(x) ** 2 for x in a)
    return {
        'count': len(a),
        'different': sum(x != y for x, y in zip(a, b)),
        'relative_l2': math.sqrt(diff2 / ref2) if ref2 else 0.0,
        'max_abs': max((abs(float(y) - float(x)) for x, y in zip(a, b)), default=0.0),
    }


def read_diag(path: Path) -> tuple[int, dict[int, tuple[int, dict[str, tuple[float, ...]]]]]:
    records = {}
    selected_layer = None
    with path.open('rb') as stream:
        while header := stream.read(DIAG_HEADER.size):
            if len(header) != DIAG_HEADER.size:
                raise ValueError(f'{path}: truncated STGDIAG4 header')
            magic, version, layer, rows, pos0, n_embd, channels, heads, value_dim, _state, *tokens = DIAG_HEADER.unpack(header)
            if magic != b'STGDIAG4' or version != 4 or not 1 <= rows <= len(tokens):
                raise ValueError(f'{path}: invalid STGDIAG4 record')
            if selected_layer is not None and layer != selected_layer:
                raise ValueError(f'{path}: layer changed within capture')
            selected_layer = layer
            dims = (n_embd, channels, channels, heads, heads, value_dim, value_dim,
                    n_embd, n_embd, n_embd)
            fields = []
            for width in dims:
                payload = stream.read(rows * width * 4)
                if len(payload) != rows * width * 4:
                    raise ValueError(f'{path}: truncated STGDIAG4 payload')
                values = struct.unpack(f'<{rows * width}f', payload)
                fields.append([values[i * width:(i + 1) * width] for i in range(rows)])
            for i in range(rows):
                position = pos0 + i
                if position in records:
                    raise ValueError(f'{path}: duplicate GDN position {position}')
                records[position] = (tokens[i], dict(zip(FIELD_NAMES, (f[i] for f in fields))))
    if selected_layer is None:
        raise ValueError(f'{path}: no GDN diagnostic records')
    return selected_layer, records


def read_o(path: Path) -> tuple[int, dict[int, tuple[int, tuple[float, ...]]]]:
    records = {}
    selected_layer = None
    with path.open('rb') as stream:
        while header := stream.read(O_HEADER.size):
            if len(header) != O_HEADER.size:
                raise ValueError(f'{path}: truncated STGDOO1 header')
            magic, version, layer, rows, pos0, value_dim, *tokens = O_HEADER.unpack(header)
            if magic != b'STGDOO1\0' or version != 1 or not 1 <= rows <= len(tokens):
                raise ValueError(f'{path}: invalid STGDOO1 record')
            if selected_layer is not None and layer != selected_layer:
                raise ValueError(f'{path}: layer changed within raw-o capture')
            selected_layer = layer
            payload = stream.read(rows * value_dim * 4)
            if len(payload) != rows * value_dim * 4:
                raise ValueError(f'{path}: truncated STGDOO1 payload')
            values = struct.unpack(f'<{rows * value_dim}f', payload)
            for i in range(rows):
                position = pos0 + i
                if position in records:
                    raise ValueError(f'{path}: duplicate raw-o position {position}')
                records[position] = (tokens[i], values[i * value_dim:(i + 1) * value_dim])
    if selected_layer is None:
        raise ValueError(f'{path}: no STGDOO1 records')
    return selected_layer, records


def compare(reference: Path, candidate: Path, reference_o: Path | None,
            candidate_o: Path | None) -> dict:
    layer_a, a = read_diag(reference)
    layer_b, b = read_diag(candidate)
    if layer_a != layer_b or set(a) != set(b):
        raise ValueError('GDN diagnostic layers or positions differ')
    result = {'schema': 1, 'layer': layer_a, 'positions': []}
    for position in sorted(a):
        token_a, fields_a = a[position]
        token_b, fields_b = b[position]
        if token_a != token_b:
            raise ValueError(f'token mismatch at position {position}')
        result['positions'].append({
            'position': position, 'token': token_a,
            'fields': {name: metrics(fields_a[name], fields_b[name]) for name in FIELD_NAMES},
        })
    if (reference_o is None) != (candidate_o is None):
        raise ValueError('raw-o captures must be supplied as a pair')
    if reference_o is not None and candidate_o is not None:
        olayer_a, oa = read_o(reference_o)
        olayer_b, ob = read_o(candidate_o)
        if olayer_a != layer_a or olayer_b != layer_b or set(oa) != set(ob):
            raise ValueError('raw-o layers or positions differ from GDN captures')
        for row in result['positions']:
            position = row['position']
            token_a, values_a = oa[position]
            token_b, values_b = ob[position]
            if token_a != row['token'] or token_b != row['token']:
                raise ValueError(f'raw-o token mismatch at position {position}')
            row['raw_o'] = metrics(values_a, values_b)
    result['first_differing_position'] = next(
        (row['position'] for row in result['positions']
         if any(item['different'] for item in row['fields'].values()) or
         ('raw_o' in row and row['raw_o']['different'])), None)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--reference-o', type=Path)
    parser.add_argument('--candidate-o', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.reference, args.candidate, args.reference_o, args.candidate_o)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
