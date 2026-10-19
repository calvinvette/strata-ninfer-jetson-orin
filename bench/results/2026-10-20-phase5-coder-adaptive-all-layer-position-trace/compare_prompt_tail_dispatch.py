#!/usr/bin/env python3
"""Compare same-position verifier activations and expert owners for short/recovery requests."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def compare_vectors(reference, candidate):
    if len(reference) != len(candidate):
        raise ValueError('activation dimensions differ')
    different = 0
    max_abs = 0.0
    delta_sq = reference_sq = 0.0
    for a, b in zip(reference, candidate):
        delta = float(b) - float(a)
        different += a != b
        max_abs = max(max_abs, abs(delta))
        delta_sq += delta * delta
        reference_sq += float(a) * float(a)
    return {'values': len(reference), 'different_values': different, 'max_abs_diff': max_abs,
            'relative_l2': math.sqrt(delta_sq / reference_sq) if reference_sq else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True,
                        help='all-layer-selected-positions.jsonl from one short/long/recovery service sequence')
    parser.add_argument('--positions', type=int, nargs='+', default=[505, 506])
    parser.add_argument('--layers', type=int, default=48)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    raw = args.capture.read_bytes()
    lines = raw.decode().splitlines()
    if not lines:
        raise ValueError('empty dispatch capture')
    header = json.loads(lines[0])
    if header.get('format') != 'strata-moe-dispatch-v3':
        raise ValueError('unsupported dispatch capture format')
    records = [json.loads(line) for line in lines[1:]]
    by_key = {}
    for row in records:
        if row['position'] in args.positions:
            by_key.setdefault((row['position'], row['layer']), []).append(row)

    position_results = []
    for position in args.positions:
        layer_results = []
        for layer in range(args.layers):
            pair = by_key.get((position, layer), [])
            if len(pair) != 2:
                raise ValueError(f'expected initial/recovery rows for position {position}, layer {layer}; found {len(pair)}')
            initial, recovery = pair
            if initial['token_id'] != recovery['token_id']:
                raise ValueError(f'token mismatch at position {position}, layer {layer}')
            activation = compare_vectors(initial['activation'], recovery['activation'])
            layer_results.append({
                'layer': layer,
                'token_id': initial['token_id'],
                'token_experts_equal': initial['ids'] == recovery['ids'],
                'expert_owners_equal': initial['route_kind'] == recovery['route_kind'],
                'initial_experts': initial['ids'],
                'recovery_experts': recovery['ids'],
                'initial_owners': initial['route_kind'],
                'recovery_owners': recovery['route_kind'],
                'activation': activation,
            })
        first_activation = next((x['layer'] for x in layer_results
                                 if x['activation']['different_values']), None)
        first_owner = next((x['layer'] for x in layer_results if not x['expert_owners_equal']), None)
        first_experts = next((x['layer'] for x in layer_results if not x['token_experts_equal']), None)
        position_results.append({
            'position': position,
            'token_id': layer_results[0]['token_id'],
            'first_differing_activation_layer': first_activation,
            'first_differing_expert_owner_layer': first_owner,
            'first_differing_expert_ids_layer': first_experts,
            'layers': layer_results,
        })
    result = {
        'capture_sha256': hashlib.sha256(raw).hexdigest(),
        'capture_bytes': len(raw),
        'model_layers': args.layers,
        'positions': position_results,
        'interpretation_limit': 'same-position verifier inputs and selected expert owners localize the first divergence, but do not alone prove which kernel or commit operation causes it',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({
        'capture_sha256': result['capture_sha256'],
        'positions': [{k: v for k, v in item.items() if k != 'layers'} for item in position_results],
    }, indent=2))


if __name__ == '__main__':
    main()
