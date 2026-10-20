#!/usr/bin/env python3
"""Compare verifier routes, expert rows, and combined MoE outputs at one layer."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIIIIQq8i')
OUTPUT_HEADER = struct.Struct('<8sIIIIQq8i')


def read_routes(path, layer, positions):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if not records or records[0].get('format') != 'strata-verify-moe-route-v1':
        raise ValueError(f'invalid verifier route capture: {path}')
    return [row for row in records[1:] if row.get('layer') == layer and row.get('position') in positions]


def read_parts(path, selected_layer, positions):
    data = path.read_bytes()
    out = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated MoE parts header in {path} at {offset}')
        values = HEADER.unpack_from(data, offset)
        magic, version, record_layer, rows, k, n_embd, pos0, *tokens = values
        offset += HEADER.size
        if magic != b'STMPART1' or version != 1 or record_layer != selected_layer or not 0 < rows <= 8:
            raise ValueError(f'invalid MoE parts header in {path}: {values[:7]}')
        n_floats = rows * k * n_embd
        n_bytes = n_floats * 4
        if len(data) - offset < n_bytes:
            raise ValueError(f'truncated MoE parts payload in {path} at {offset}')
        floats = struct.unpack(f'<{n_floats}f', data[offset:offset + n_bytes])
        offset += n_bytes
        for row in range(rows):
            position = pos0 + row
            if position in positions:
                start = row * k * n_embd
                out.append({'position': position, 'token': tokens[row], 'k': k, 'n_embd': n_embd,
                            'parts': floats[start:start + k * n_embd]})
    return data, out


def read_outputs(path, selected_layer, positions):
    data = path.read_bytes()
    out = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < OUTPUT_HEADER.size:
            raise ValueError(f'truncated MoE output header in {path} at {offset}')
        values = OUTPUT_HEADER.unpack_from(data, offset)
        magic, version, record_layer, rows, reserved, n_embd, pos0, *tokens = values
        offset += OUTPUT_HEADER.size
        if magic != b'STMOEOUT' or version != 1 or record_layer != selected_layer or reserved != 0 or not 0 < rows <= 8:
            raise ValueError(f'invalid MoE output header in {path}: {values[:8]}')
        n_floats = rows * n_embd
        n_bytes = n_floats * 4
        if len(data) - offset < 2 * n_bytes:
            raise ValueError(f'truncated MoE output payload in {path} at {offset}')
        shared = struct.unpack(f'<{n_floats}f', data[offset:offset + n_bytes])
        offset += n_bytes
        combined = struct.unpack(f'<{n_floats}f', data[offset:offset + n_bytes])
        offset += n_bytes
        for row in range(rows):
            position = pos0 + row
            if position in positions:
                start = row * n_embd
                out.append({'position': position, 'token': tokens[row], 'n_embd': n_embd,
                            'shared': shared[start:start + n_embd],
                            'combined': combined[start:start + n_embd]})
    return data, out


def summarize(a, b):
    if len(a) != len(b):
        raise ValueError('captured MoE vector dimensions differ')
    if any(not math.isfinite(x) for x in a + b):
        raise ValueError('captured MoE vector contains a non-finite value')
    different = 0
    max_abs = 0.0
    delta_sq = ref_sq = 0.0
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
    parser.add_argument('--layer', type=int, default=25)
    parser.add_argument('--positions', type=int, nargs='+', default=[511])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if any(p < 0 for p in args.positions) or args.positions != sorted(set(args.positions)):
        parser.error('--positions must be strictly increasing non-negative integers')
    if not 0 <= args.layer < 48:
        parser.error('--layer must be in [0, 47]')
    selected = set(args.positions)
    route_rows = read_routes(args.run / 'verify-moe-routes.jsonl', args.layer, selected)
    parts_raw, parts_rows = read_parts(args.run / 'verify-moe-parts.bin', args.layer, selected)
    output_path = args.run / 'verify-moe-output.bin'
    output_raw, output_rows = read_outputs(output_path, args.layer, selected) if output_path.is_file() else (None, None)

    grouped = {}
    for kind, rows in (('routes', route_rows), ('parts', parts_rows), ('outputs', output_rows or [])):
        for row in rows:
            grouped.setdefault(row['position'], {}).setdefault(kind, []).append(row)
    if set(grouped) != selected:
        raise ValueError(f'expected selected positions {args.positions}; observed {sorted(grouped)}')

    comparisons = {}
    for position in args.positions:
        group = grouped[position]
        if len(group.get('routes', [])) != 2 or len(group.get('parts', [])) != 2 or \
                (output_rows is not None and len(group.get('outputs', [])) != 2):
            raise ValueError(f'expected initial/recovery records at {position}; got '
                             f'{ {key: len(value) for key, value in group.items()} }')
        first_route, recovery_route = group['routes']
        first_parts, recovery_parts = group['parts']
        for row, route in ((first_parts, first_route), (recovery_parts, recovery_route)):
            if (row['position'], row['token'], row['k'], row['n_embd']) != (
                    route['position'], route['token_id'], len(route['ids']), 2560):
                raise ValueError(f'route/parts position or shape mismatch: {route}, {row}')
        route_same = all(first_route[key] == recovery_route[key]
                         for key in ('token_id', 'position', 'ids', 'weights'))
        result = {
            'token_ids': [first_route['token_id'], recovery_route['token_id']],
            'expert_ids': {'initial': first_route['ids'], 'recovery': recovery_route['ids']},
            'router_weights': {'initial': first_route['weights'], 'recovery': recovery_route['weights']},
            'routes_and_router_weights_identical': route_same,
            'all_expert_rows_after_moe_hit_add': summarize(first_parts['parts'], recovery_parts['parts']),
        }
        result['per_expert_rank'] = {
            str(rank): {'initial_expert': first_route['ids'][rank],
                        'recovery_expert': recovery_route['ids'][rank],
                        'output': summarize(first_parts['parts'][rank * 2560:(rank + 1) * 2560],
                                            recovery_parts['parts'][rank * 2560:(rank + 1) * 2560])}
            for rank in range(len(first_route['ids']))
        }
        if output_rows is not None:
            first_output, recovery_output = group['outputs']
            for row, route in ((first_output, first_route), (recovery_output, recovery_route)):
                if (row['position'], row['token'], row['n_embd']) != (
                        route['position'], route['token_id'], 2560):
                    raise ValueError(f'route/output position or shape mismatch: {route}, {row}')
            result['shared_expert_output'] = summarize(first_output['shared'], recovery_output['shared'])
            result['combined_moe_output_before_residual'] = summarize(first_output['combined'], recovery_output['combined'])
        comparisons[str(position)] = result

    result = {
        'scope': f'same-service initial/recovery Coder IQ1_M verifier MoE capture at model layer {args.layer}',
        'layer': args.layer,
        'positions': args.positions,
        'binary_sha256': json.loads((args.run / 'analysis.json').read_text())['binary_sha256'],
        'raw_capture_sha256': {
            'routes': hashlib.sha256((args.run / 'verify-moe-routes.jsonl').read_bytes()).hexdigest(),
            'parts': hashlib.sha256(parts_raw).hexdigest(),
            'outputs': hashlib.sha256(output_raw).hexdigest() if output_raw is not None else None,
        },
        'position_comparisons': comparisons,
        'limits': ['post-combine residual/hyper-connection write and next-layer GDN state transition were not captured'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'positions': args.positions,
                      'route_and_router_weights_identical': {
                          position: item['routes_and_router_weights_identical']
                          for position, item in comparisons.items()},
                      'combined_moe_different_values': {
                          position: item.get('combined_moe_output_before_residual', {}).get('different_values')
                          for position, item in comparisons.items()}}, indent=2))


if __name__ == '__main__':
    main()
