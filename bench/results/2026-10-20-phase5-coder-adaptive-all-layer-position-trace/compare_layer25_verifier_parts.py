#!/usr/bin/env python3
"""Compare exact verifier expert rows and router weights at Coder layer 25."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIIIIQq8i')


def read_routes(path):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if not records or records[0].get('format') != 'strata-verify-moe-route-v1':
        raise ValueError(f'invalid verifier route capture: {path}')
    return [row for row in records[1:] if row.get('layer') == 25 and row.get('position') == 511]


def read_parts(path):
    data = path.read_bytes()
    out = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated MoE parts header in {path} at {offset}')
        values = HEADER.unpack_from(data, offset)
        magic, version, layer, rows, k, n_embd, pos0, *tokens = values
        offset += HEADER.size
        if magic != b'STMPART1' or version != 1 or layer != 25:
            raise ValueError(f'invalid MoE parts header in {path}: {values[:7]}')
        n_floats = rows * k * n_embd
        n_bytes = n_floats * 4
        if len(data) - offset < n_bytes:
            raise ValueError(f'truncated MoE parts payload in {path} at {offset}')
        payload = data[offset:offset + n_bytes]
        floats = struct.unpack(f'<{n_floats}f', payload)
        offset += n_bytes
        out.append({'rows': rows, 'k': k, 'n_embd': n_embd, 'pos0': pos0,
                    'tokens': tokens[:rows], 'parts': floats})
    return out


def summarize(a, b):
    different = 0
    max_abs = 0.0
    delta_sq = 0.0
    ref_sq = 0.0
    for x, y in zip(a, b):
        d = float(y) - float(x)
        different += x != y
        max_abs = max(max_abs, abs(d))
        delta_sq += d * d
        ref_sq += float(x) * float(x)
    return {
        'values': len(a),
        'different_values': different,
        'max_abs_diff': max_abs,
        'relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None,
        'initial_f32_sha256': hashlib.sha256(struct.pack(f'<{len(a)}f', *a)).hexdigest(),
        'recovery_f32_sha256': hashlib.sha256(struct.pack(f'<{len(b)}f', *b)).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True, help='same-service run directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    route_rows = read_routes(args.run / 'verify-moe-routes.jsonl')
    parts_rows = read_parts(args.run / 'verify-moe-parts.bin')
    if len(route_rows) != 2 or len(parts_rows) != 2:
        raise ValueError(f'expected initial/recovery capture pairs, got routes={len(route_rows)} parts={len(parts_rows)}')
    for route, parts in zip(route_rows, parts_rows):
        if (parts['rows'], parts['k'], parts['n_embd'], parts['pos0'], parts['tokens']) != (
                1, 10, 2560, 511, [route['token_id']]):
            raise ValueError(f'route/parts position or shape mismatch: {route}, {parts}')
        if route['token_id'] != 271 or route['position'] != 511:
            raise ValueError(f'unexpected target row: {route}')
    first_route, recovery_route = route_rows
    if any(first_route[key] != recovery_route[key] for key in ('token_id', 'position', 'ids', 'weights')):
        raise ValueError('initial/recovery verifier token, routes, or router weights differ')
    first_parts, recovery_parts = parts_rows
    per_expert = {}
    for rank, expert in enumerate(first_route['ids']):
        start = rank * 2560
        a = first_parts['parts'][start:start + 2560]
        b = recovery_parts['parts'][start:start + 2560]
        per_expert[str(expert)] = summarize(a, b)
    result = {
        'scope': 'same-service initial/recovery Coder IQ1_M verifier row at model layer 25',
        'position': 511,
        'token_id': 271,
        'binary_sha256': json.loads((args.run / 'analysis.json').read_text())['binary_sha256'],
        'route_and_router_weights_identical': True,
        'expert_ids': first_route['ids'],
        'router_weights': first_route['weights'],
        'all_expert_rows_after_moe_hit_add': summarize(first_parts['parts'], recovery_parts['parts']),
        'per_expert': per_expert,
        'limits': ['expert rows were captured before weighted combine; shared-expert output and final layer output were not captured'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
