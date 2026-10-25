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


def floats(path: Path, header: struct.Struct, magic: bytes, fields: int,
           count: int) -> tuple[tuple[float, ...], tuple]:
    raw = path.read_bytes()
    if len(raw) < header.size:
        raise ValueError(f'{path}: truncated header')
    values = header.unpack_from(raw)
    if values[0] != magic or values[1] != fields:
        raise ValueError(f'{path}: unexpected format/version {values[:2]}')
    n = count(values)
    if len(raw) != header.size + n * 4:
        raise ValueError(f'{path}: expected {header.size + n * 4} bytes, got {len(raw)}')
    return struct.unpack_from(f'<{n}f', raw, header.size), values


INPUT_HEADER = struct.Struct('<8sIIIIQq8i')
ROW_HEADER = struct.Struct('<8sIIIIQqii')


def read_route(path: Path) -> dict:
    lines = path.read_text().splitlines()
    if len(lines) != 2 or json.loads(lines[0]) != {'format': 'strata-verify-moe-route-v1', 'k': 10}:
        raise ValueError(f'{path}: expected one captured top-10 route')
    return json.loads(lines[1])


def analyze_layer(root: Path, layer: int, reference: str, candidate: str) -> dict:
    def path(arm: str, kind: str) -> Path:
        return root / f'run-layer{layer}' / f'{arm}.layer{layer}.{kind}'

    routes = [read_route(path(arm, 'route')) for arm in (reference, candidate)]
    if (routes[0]['layer'], routes[0]['position'], routes[0]['token_id']) != \
       (routes[1]['layer'], routes[1]['position'], routes[1]['token_id']):
        raise ValueError(f'layer {layer}: route record identity differs')
    input_vectors, parts_vectors, outputs = [], [], []
    for arm in (reference, candidate):
        vec, ih = floats(path(arm, 'input'), INPUT_HEADER, b'STMOINP1', 1,
                         lambda h: int(h[5]))
        if (ih[2], ih[3], ih[5], ih[6], ih[7]) != (layer, 1, 2560, routes[0]['position'], routes[0]['token_id']):
            raise ValueError(f'{arm} layer {layer}: input header does not match captured route')
        input_vectors.append(vec)
        vec, ph = floats(path(arm, 'parts'), ROW_HEADER, b'STMPART2', 2,
                         lambda h: int(h[3] * h[5]))
        if (ph[2], ph[3], ph[5], ph[6], ph[7], ph[8]) != \
           (layer, 10, 2560, routes[0]['position'], -1, routes[0]['token_id']):
            raise ValueError(f'{arm} layer {layer}: parts header does not match captured route')
        parts_vectors.append(vec)
        vec, oh = floats(path(arm, 'output'), ROW_HEADER, b'MOEOUT02', 2,
                         lambda h: int(2 * h[5]))
        if (oh[2], oh[3], oh[5], oh[6], oh[7], oh[8]) != \
           (layer, 1, 2560, routes[0]['position'], -1, routes[0]['token_id']):
            raise ValueError(f'{arm} layer {layer}: output header does not match captured route')
        outputs.append((vec[:2560], vec[2560:]))
    return {'position': routes[0]['position'], 'token_id': routes[0]['token_id'],
            'route_ids_equal': routes[0]['ids'] == routes[1]['ids'],
            'max_route_weight_abs_delta': max(abs(a - b) for a, b in zip(routes[0]['weights'], routes[1]['weights'])),
            'input': metrics(*input_vectors), 'expert_parts': metrics(*parts_vectors),
            'shared_output': metrics(outputs[0][0], outputs[1][0]),
            'combined_output': metrics(outputs[0][1], outputs[1][1])}


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
