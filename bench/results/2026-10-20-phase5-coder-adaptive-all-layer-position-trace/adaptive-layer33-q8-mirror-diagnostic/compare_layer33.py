#!/usr/bin/env python3
"""Join three-request layer-33 routes and verifier expert outputs."""
import hashlib
import argparse
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTS_HEADER = struct.Struct('<8sIIIIQq8i')
OUTPUT_HEADER = struct.Struct('<8sIIIIQq8i')
WIDTH = 2560
EXPERT = 57
LAYER = 33
POSITION = 511


def vector_summary(a, b):
    if len(a) != len(b) or any(not math.isfinite(x) for x in a + b):
        raise ValueError('invalid or mismatched float vectors')
    delta = [float(y) - float(x) for x, y in zip(a, b)]
    reference = math.fsum(float(x) ** 2 for x in a)
    return {
        'values': len(a),
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs_diff': max(map(abs, delta), default=0.0),
        'relative_l2': math.sqrt(math.fsum(x * x for x in delta) / reference) if reference else None,
    }


def read_parts(path):
    raw = path.read_bytes()
    rows, offset = [], 0
    while offset < len(raw):
        magic, version, layer, count, k, width, pos0, *tokens = PARTS_HEADER.unpack_from(raw, offset)
        offset += PARTS_HEADER.size
        if magic != b'STMPART1' or version != 1 or layer != LAYER or count != 1 or width != WIDTH:
            raise ValueError(f'invalid expert-parts record at byte {offset - PARTS_HEADER.size}')
        size = count * k * width * 4
        values = struct.unpack_from(f'<{count * k * width}f', raw, offset)
        offset += size
        if pos0 == POSITION:
            rows.append({'token': tokens[0], 'k': k, 'parts': values})
    if offset != len(raw) or len(rows) != 3:
        raise ValueError(f'expected three layer-{LAYER}, position-{POSITION} parts rows; found {len(rows)}')
    return raw, rows


def read_outputs(path):
    raw = path.read_bytes()
    rows, offset = [], 0
    while offset < len(raw):
        magic, version, layer, count, reserved, width, pos0, *tokens = OUTPUT_HEADER.unpack_from(raw, offset)
        offset += OUTPUT_HEADER.size
        if magic != b'STMOEOUT' or version != 1 or layer != LAYER or count != 1 or reserved or width != WIDTH:
            raise ValueError(f'invalid combined-output record at byte {offset - OUTPUT_HEADER.size}')
        size = width * 4
        shared = struct.unpack_from(f'<{width}f', raw, offset); offset += size
        combined = struct.unpack_from(f'<{width}f', raw, offset); offset += size
        if pos0 == POSITION:
            rows.append({'token': tokens[0], 'shared': shared, 'combined': combined})
    if offset != len(raw) or len(rows) != 3:
        raise ValueError(f'expected three layer-{LAYER}, position-{POSITION} output rows; found {len(rows)}')
    return raw, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True,
                        help='campaign directory with delayed-control and adaptive-cap8 arms')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = {'scope': 'layer-33 verifier expert rows across three same-service short requests',
              'layer': LAYER, 'position': POSITION, 'expert': EXPERT, 'arms': {}}
    for arm in ('delayed-control', 'adaptive-cap8'):
        run = args.run_dir / arm / 'result'
        dispatch = [json.loads(line) for line in (run / 'all-layer-position511.jsonl').read_text().splitlines()]
        if not dispatch or dispatch[0].get('format') != 'strata-moe-dispatch-v3':
            raise ValueError(f'{arm}: invalid dispatch trace')
        dispatch = [row for row in dispatch[1:] if row['layer'] == LAYER and row['position'] == POSITION]
        verifier_routes = [json.loads(line) for line in (run / 'verify-moe-routes.jsonl').read_text().splitlines()]
        if not verifier_routes or verifier_routes[0].get('format') != 'strata-verify-moe-route-v1':
            raise ValueError(f'{arm}: invalid verifier route trace')
        verifier_routes = [row for row in verifier_routes[1:] if row.get('layer') == LAYER and row.get('position') == POSITION]
        parts_raw, parts = read_parts(run / 'verify-moe-parts.bin')
        outputs_raw, outputs = read_outputs(run / 'verify-moe-output.bin')
        if not (len(dispatch) == len(verifier_routes) == len(parts) == len(outputs) == 3):
            raise ValueError(f'{arm}: route/output row counts differ')
        request_rows = []
        for index, (route, verifier_route, part, combined) in enumerate(zip(dispatch, verifier_routes, parts, outputs)):
            if route['ids'] != verifier_route['ids'] or route['token_id'] != verifier_route['token_id']:
                raise ValueError(f'{arm} request {index}: route identity mismatch')
            if route['token_id'] != part['token'] or route['token_id'] != combined['token'] or route['k'] != part['k']:
                raise ValueError(f'{arm} request {index}: token or shape mismatch')
            rank = route['ids'].index(EXPERT) if EXPERT in route['ids'] else None
            expert_row = part['parts'][rank * WIDTH:(rank + 1) * WIDTH] if rank is not None else None
            request_rows.append({'token_id': route['token_id'], 'activation': route['activation'],
                                 'expert_ids': route['ids'], 'route_kind': route['route_kind'],
                                 'router_weights': verifier_route['weights'], 'expert_rank': rank,
                                 'expert_output': expert_row, 'shared_output': combined['shared'],
                                 'combined_output': combined['combined']})
        transitions = []
        for i, j in ((0, 1), (1, 2)):
            a, b = request_rows[i], request_rows[j]
            if a['token_id'] != b['token_id']:
                raise ValueError(f'{arm} transition {i}->{j}: token IDs changed')
            rank_a = a['expert_ids'].index(EXPERT) if EXPERT in a['expert_ids'] else None
            rank_b = b['expert_ids'].index(EXPERT) if EXPERT in b['expert_ids'] else None
            transitions.append({
                'requests': [i, j], 'token_id': a['token_id'],
                'activation_bit_identical': a['activation'] == b['activation'],
                'expert_ids_bit_identical': a['expert_ids'] == b['expert_ids'],
                'router_weights_bit_identical': a['router_weights'] == b['router_weights'],
                'owner_before': a['route_kind'][rank_a] if rank_a is not None else None,
                'owner_after': b['route_kind'][rank_b] if rank_b is not None else None,
                'expert_output': vector_summary(a['expert_output'], b['expert_output'])
                                 if rank_a is not None and rank_b is not None else None,
                'shared_output': vector_summary(a['shared_output'], b['shared_output']),
                'combined_output': vector_summary(a['combined_output'], b['combined_output']),
            })
        output['arms'][arm] = {
            'records': len(request_rows), 'expert_rank': request_rows[0]['expert_rank'],
            'route_input_and_ids_match_across_requests': all(
                row['activation'] == request_rows[0]['activation'] and row['expert_ids'] == request_rows[0]['expert_ids']
                for row in request_rows),
            'transitions': transitions,
            'capture_sha256': {
                'dispatch': hashlib.sha256((run / 'all-layer-position511.jsonl').read_bytes()).hexdigest(),
                'parts': hashlib.sha256(parts_raw).hexdigest(),
                'combined': hashlib.sha256(outputs_raw).hexdigest(),
            },
        }
    path = args.output or args.run_dir / 'layer33-analysis.json'
    path.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({arm: data['transitions'] for arm, data in output['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
