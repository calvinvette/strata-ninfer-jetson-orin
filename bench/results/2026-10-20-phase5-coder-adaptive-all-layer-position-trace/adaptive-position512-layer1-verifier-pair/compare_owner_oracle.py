#!/usr/bin/env python3
"""Match captured verifier expert rows to independent same-input CPU/GPU oracles."""
import argparse
import hashlib
import importlib.util
import json
import math
import struct
from pathlib import Path


def load_parts_reader():
    path = Path(__file__).resolve().parents[1] / 'compare_layer25_verifier_parts.py'
    spec = importlib.util.spec_from_file_location('verifier_parts', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_f32(path):
    raw = path.read_bytes()
    if len(raw) % 4:
        raise ValueError(f'non-float32 oracle file: {path}')
    return raw, struct.unpack(f'<{len(raw) // 4}f', raw)


def compare(reference, observed):
    if len(reference) != len(observed):
        raise ValueError('oracle and service expert output dimensions differ')
    diff = [float(b) - float(a) for a, b in zip(reference, observed)]
    norm = math.fsum(float(x) * float(x) for x in reference)
    return {
        'values': len(reference),
        'different_values': sum(a != b for a, b in zip(reference, observed)),
        'max_abs_diff': max((abs(x) for x in diff), default=0.0),
        'relative_l2': math.sqrt(math.fsum(x * x for x in diff) / norm) if norm else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='randomized delayed/adaptive pair directory')
    parser.add_argument('--layer', type=int, default=1)
    parser.add_argument('--position', type=int, default=512)
    parser.add_argument('--experts', type=int, nargs='+', default=[95, 11, 205])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.layer < 0 or args.layer >= 48 or args.position < 0:
        parser.error('--layer must be in [0, 47] and --position must be non-negative')
    readers = load_parts_reader()

    all_layer_rows = {}
    dispatch_name = ('all-layer-position511.jsonl' if args.position == 511
                     else 'all-layer-selected-positions.jsonl')
    for arm in ('delayed-control', 'adaptive-cap8'):
        lines = (args.root / arm / 'result' / dispatch_name).read_text().splitlines()
        if not lines or json.loads(lines[0]).get('format') != 'strata-moe-dispatch-v3':
            raise ValueError(f'invalid all-layer dispatch capture for {arm}')
        matches = [json.loads(line) for line in lines[1:]
                   if json.loads(line).get('layer') == args.layer and json.loads(line).get('position') == args.position]
        if len(matches) != 2:
            raise ValueError(f'{arm}: expected initial/recovery layer-{args.layer} rows, found {len(matches)}')
        all_layer_rows[arm] = matches

    oracle = {}
    oracle_hashes = {}
    for expert in args.experts:
        directory = args.root / f'expert{expert}-oracle'
        oracle[expert] = {}
        oracle_hashes[expert] = {}
        for owner in ('cpu', 'gpu'):
            path = directory / f'layer-{args.layer}-expert-{expert}-{owner}-output.f32'
            raw, values = read_f32(path)
            oracle[expert][owner] = values
            oracle_hashes[expert][owner] = hashlib.sha256(raw).hexdigest()

    service = {}
    routes = {}
    for arm in ('delayed-control', 'adaptive-cap8'):
        result = args.root / arm / 'result'
        _, part_rows = readers.read_parts(result / 'verify-moe-parts.bin', args.layer, {args.position})
        route_rows = [json.loads(line) for line in (result / 'verify-moe-routes.jsonl').read_text().splitlines()[1:]
                   if json.loads(line).get('layer') == args.layer and
                      json.loads(line).get('position') == args.position]
        if len(part_rows) != 2 or len(route_rows) != 2:
            raise ValueError(f'{arm}: expected two verifier expert-part and route records')
        service[arm] = []
        routes[arm] = []
        for record_index, (parts, route, trace) in enumerate(zip(part_rows, route_rows, all_layer_rows[arm])):
            if parts['token'] != route['token_id'] or route['ids'] != trace['ids']:
                raise ValueError(f'{arm} record {record_index}: selected route and verifier row metadata mismatch')
            rows = {}
            for rank, expert in enumerate(route['ids']):
                if expert not in args.experts:
                    continue
                vector = parts['parts'][rank * 2560:(rank + 1) * 2560]
                rows[str(expert)] = {
                    'rank': rank,
                    'cpu_oracle': compare(oracle[expert]['cpu'], vector),
                    'gpu_oracle': compare(oracle[expert]['gpu'], vector),
                    'exact_owner_match': ('cpu' if vector == oracle[expert]['cpu'] else
                                          'gpu' if vector == oracle[expert]['gpu'] else None),
                    'dispatch_trace_route_kind': trace['route_kind'][rank],
                }
            if set(rows) != {str(e) for e in args.experts}:
                raise ValueError(f'{arm} record {record_index}: one or more target experts were not routed')
            service[arm].append(rows)
            routes[arm].append({key: route[key] for key in ('position', 'token_id', 'ids', 'weights')})

    for arm in ('delayed-control', 'adaptive-cap8'):
        if routes[arm][0] != routes[arm][1]:
            raise ValueError(f'{arm}: verifier route IDs or weights changed across initial/recovery rows')
        if all_layer_rows[arm][0]['activation'] != all_layer_rows[arm][1]['activation']:
            raise ValueError(f'{arm}: selected layer-{args.layer} input activation changed across requests')
    reference_activation = all_layer_rows['delayed-control'][0]['activation']
    if any(row['activation'] != reference_activation
           for arm in ('delayed-control', 'adaptive-cap8') for row in all_layer_rows[arm]):
        raise ValueError(f'selected layer-{args.layer} input activation differs across paired arms/requests')

    result = {
        'scope': f'same-input layer-{args.layer} verifier expert rows versus independent native CPU/GPU outputs',
        'position': args.position,
        'layer': args.layer,
        'experts': args.experts,
        'oracle_sha256': oracle_hashes,
        'activation_sha256': hashlib.sha256(struct.pack(
            f'<{len(all_layer_rows["delayed-control"][0]["activation"])}f',
            *all_layer_rows['delayed-control'][0]['activation'])).hexdigest(),
        'route_identity_across_arms_and_requests': all(
            routes['delayed-control'][i] == routes['adaptive-cap8'][j]
            for i in range(2) for j in range(2)),
        'layer_input_bitwise_identical_across_all_rows': True,
        'dispatch_trace_owner_kinds': {
            arm: [{str(expert): row['route_kind'][row['ids'].index(expert)]
                   for expert in args.experts} for row in all_layer_rows[arm]]
            for arm in ('delayed-control', 'adaptive-cap8')},
        'service_rows': service,
        'interpretation_limit': 'the numeric fingerprint identifies which independent owner oracle matches the captured row; it does not by itself explain why the separate dispatch-owner trace disagrees',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({arm: [
        {expert: row[expert]['exact_owner_match'] for expert in map(str, args.experts)}
        for row in service[arm]] for arm in service}, indent=2))


if __name__ == '__main__':
    main()
