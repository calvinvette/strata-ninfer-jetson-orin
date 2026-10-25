#!/usr/bin/env python3
"""Compare opt-in Strata verifier MoE captures from paired backend runs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct


def metrics(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate):
        raise ValueError(f'vector lengths differ: {len(reference)} vs {len(candidate)}')
    delta = [b - a for a, b in zip(reference, candidate)]
    norm = math.sqrt(math.fsum(x * x for x in reference))
    return {'count': len(reference), 'different': sum(a != b for a, b in zip(reference, candidate)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in delta)) / max(norm, 1e-300),
            'max_abs': max((abs(x) for x in delta), default=0.0),
            'rms_abs': math.sqrt(math.fsum(x * x for x in delta) / len(delta)) if delta else 0.0}


def float_records(path: Path, header: struct.Struct, magic: bytes, fields: int,
                  count) -> list[tuple[tuple[float, ...], tuple]]:
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < header.size:
            raise ValueError(f'{path}: truncated record header at {offset}')
        values = header.unpack_from(raw, offset)
        if values[0] != magic or values[1] != fields:
            raise ValueError(f'{path}: unexpected format/version {values[:2]} at {offset}')
        n = count(values)
        end = offset + header.size + n * 4
        if end > len(raw):
            raise ValueError(f'{path}: truncated float payload at {offset}')
        vectors = struct.unpack_from(f'<{n}f', raw, offset + header.size)
        records.append((vectors, values))
        offset = end
    if not records:
        raise ValueError(f'{path}: no records')
    return records


INPUT_HEADER = struct.Struct('<8sIIIIQq8i')
ROW_HEADER = struct.Struct('<8sIIIIQqii')


def read_routes(path: Path) -> list[dict]:
    lines = path.read_text().splitlines()
    if len(lines) < 2 or json.loads(lines[0]) != {'format': 'strata-verify-moe-route-v1', 'k': 10}:
        raise ValueError(f'{path}: expected captured top-10 routes')
    return [json.loads(line) for line in lines[1:]]


def analyze_layer(root: Path, layer: int, reference: str, candidate: str) -> dict:
    def path(arm: str, kind: str) -> Path:
        return root / f'run-layer{layer}' / f'{arm}.layer{layer}.{kind}'

    routes = [read_routes(path(arm, 'route')) for arm in (reference, candidate)]
    route_maps = [{row['position']: row for row in arm} for arm in routes]
    if route_maps[0].keys() != route_maps[1].keys():
        raise ValueError(f'layer {layer}: captured route positions differ')
    captures = []
    position_results = []
    for arm in (reference, candidate):
        inputs = {}
        for vec, ih in float_records(path(arm, 'input'), INPUT_HEADER, b'STMOINP1', 1,
                                     lambda h: int(h[3] * h[5])):
            if (ih[2], ih[5]) != (layer, 2560):
                raise ValueError(f'{arm} layer {layer}: invalid input header')
            for row in range(ih[3]):
                position = ih[6] + row
                inputs[position] = (vec[row * 2560:(row + 1) * 2560], ih[7 + row])
        parts = {}
        for vec, ph in float_records(path(arm, 'parts'), ROW_HEADER, b'STMPART2', 2,
                                     lambda h: int(h[3] * h[5])):
            if (ph[2], ph[3], ph[5], ph[7]) != (layer, 10, 2560, -1):
                raise ValueError(f'{arm} layer {layer}: invalid parts header')
            parts[ph[6]] = (vec, ph[8])
        outputs = {}
        for vec, oh in float_records(path(arm, 'output'), ROW_HEADER, b'MOEOUT02', 2,
                                     lambda h: int(2 * h[3] * h[5])):
            if (oh[2], oh[3], oh[5], oh[7]) != (layer, 1, 2560, -1):
                raise ValueError(f'{arm} layer {layer}: invalid output header')
            outputs[oh[6]] = (vec[:2560], vec[2560:], oh[8])
        captures.append((inputs, parts, outputs))

    for position in sorted(route_maps[0]):
        route_a, route_b = route_maps[0][position], route_maps[1][position]
        if (route_a['layer'], route_a['position'], route_a['token_id']) != \
           (route_b['layer'], route_b['position'], route_b['token_id']):
            raise ValueError(f'layer {layer}, position {position}: route identity differs')
        ia, ib = captures[0][0].get(position), captures[1][0].get(position)
        pa, pb = captures[0][1].get(position), captures[1][1].get(position)
        oa, ob = captures[0][2].get(position), captures[1][2].get(position)
        if not all((ia, ib, pa, pb, oa, ob)):
            raise ValueError(f'layer {layer}, position {position}: one or more capture records are missing')
        if ia[1] != ib[1] or pa[1] != pb[1] or oa[2] != ob[2] or oa[2] != route_a['token_id']:
            raise ValueError(f'layer {layer}, position {position}: captured token IDs differ')
        # Preserve each position's compact comparison independently.
        position_results.append({
            'position': position, 'token_id': route_a['token_id'],
            'route_ids_equal': route_a['ids'] == route_b['ids'],
            'max_route_weight_abs_delta': max(abs(a - b) for a, b in zip(route_a['weights'], route_b['weights'])),
            'input': metrics(ia[0], ib[0]), 'expert_parts': metrics(pa[0], pb[0]),
            'per_expert_parts': [
                {'rank': rank, 'expert_id': route_a['ids'][rank],
                 **metrics(pa[0][rank * 2560:(rank + 1) * 2560],
                           pb[0][rank * 2560:(rank + 1) * 2560])}
                for rank in range(10)],
            'shared_output': metrics(oa[0], ob[0]),
            'combined_output': metrics(oa[1], ob[1])})
    return {'positions': position_results}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True,
                    help='run parent containing run-layerN directories')
    ap.add_argument('--layers', type=int, nargs='+', required=True)
    ap.add_argument('--reference', default='strata-control')
    ap.add_argument('--candidate', default='ninfer-control')
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    result = {'schema': 1, 'scope': 'paired verifier route/input/parts/output captures',
              'reference': a.reference, 'candidate': a.candidate,
              'layers': {str(i): analyze_layer(a.root, i, a.reference, a.candidate) for i in a.layers}}
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
