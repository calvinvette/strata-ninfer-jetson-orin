#!/usr/bin/env python3
"""Compare all four same-service verifier MoE captures for one layer/position."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('moe_parts', ROOT / 'compare_layer25_verifier_parts.py')
moe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(moe)
REQUESTS = ['short-512', 'short-512-intermediate', 'short-512-recovery', 'short-512-continuation-1']
TRANSITIONS = ((0, 1), (1, 2), (2, 3), (0, 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--layer', type=int, required=True)
    ap.add_argument('--position', type=int, required=True)
    args = ap.parse_args()
    result = {'scope': 'same-service verifier MoE route, parts and outputs', 'layer': args.layer,
              'position': args.position, 'requests': REQUESTS, 'arms': {}}
    for arm in ('adaptive-cap8', 'delayed-control'):
        run = args.run_dir / arm / 'result'
        routes = moe.read_routes(run / 'verify-moe-routes.jsonl', args.layer, {args.position})
        _, parts = moe.read_parts(run / 'verify-moe-parts.bin', args.layer, {args.position})
        _, outputs = moe.read_outputs(run / 'verify-moe-output.bin', args.layer, {args.position})
        if not (len(routes) == len(parts) == len(outputs) == 4):
            raise ValueError(f'{arm}: expected four route/parts/output rows, found {len(routes)}/{len(parts)}/{len(outputs)}')
        for route, part, output in zip(routes, parts, outputs):
            if ((route['token_id'], route['position']) != (part['token'], part['position']) or
                    (route['token_id'], route['position']) != (output['token'], output['position'])):
                raise ValueError(f'{arm}: token/position identity mismatch')
        rows = []
        for i, j in TRANSITIONS:
            route_a, route_b = routes[i], routes[j]
            part_a, part_b = parts[i], parts[j]
            output_a, output_b = outputs[i], outputs[j]
            rows.append({
                'requests': [REQUESTS[i], REQUESTS[j]],
                'token_ids_equal': route_a['token_id'] == route_b['token_id'],
                'expert_ids_equal': route_a['ids'] == route_b['ids'],
                'router_weights_equal': route_a['weights'] == route_b['weights'],
                'expert_parts': moe.summarize(part_a['parts'], part_b['parts']),
                'shared_output': moe.summarize(output_a['shared'], output_b['shared']),
                'combined_output': moe.summarize(output_a['combined'], output_b['combined']),
                'per_expert_differences': [
                    {'rank': rank, 'expert_ids': [route_a['ids'][rank], route_b['ids'][rank]],
                     **moe.summarize(part_a['parts'][rank * 2560:(rank + 1) * 2560],
                                     part_b['parts'][rank * 2560:(rank + 1) * 2560])}
                    for rank in range(part_a['k'])],
            })
        result['arms'][arm] = rows
    output_path = args.run_dir / f'layer{args.layer}-moe-sequence-analysis.json'
    output_path.write_text(json.dumps(result, indent=2) + '\n')
    for arm, rows in result['arms'].items():
        print(arm)
        for row in rows:
            print(row['requests'], 'IDs', row['expert_ids_equal'], 'weights', row['router_weights_equal'],
                  'parts', row['expert_parts']['different_values'], 'shared', row['shared_output']['different_values'],
                  'combined', row['combined_output']['different_values'])


if __name__ == '__main__':
    main()
