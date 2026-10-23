#!/usr/bin/env python3
"""Validate the current-source position-515 owner and committed-state capture."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

STATE_HEADER = struct.Struct('<8sIiqQQii')
PARTS_HEADER = struct.Struct('<8sIIIIQq8i')
OUTPUT_HEADER = struct.Struct('<8sIIIIQq8i')
INPUT_HEADER = struct.Struct('<8sIIIIQq8i')
WIDTH = 2560
POSITION = 515
EXPERT = 129


def read_rows(path, header, magic, layer):
    raw = path.read_bytes()
    rows = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < header.size:
            raise ValueError(f'{path}: truncated header at {offset}')
        fields = header.unpack_from(raw, offset)
        offset += header.size
        got_magic, version, got_layer, nrows, extra, width, pos0, *tokens = fields
        arrays = 1 if magic == b'STMPART1' else 2
        if got_magic != magic or version != 1 or got_layer != layer or not 0 < nrows <= 8 or \
                width != WIDTH or (arrays == 1 and extra != 10) or (arrays == 2 and extra != 0):
            raise ValueError(f'{path}: invalid record header {fields[:7]}')
        size = nrows * width * (extra if arrays == 1 else 2) * 4
        if len(raw) - offset < size:
            raise ValueError(f'{path}: truncated payload at {offset}')
        payload = raw[offset:offset + size]
        offset += size
        for row in range(nrows):
            position = pos0 + row
            if position == POSITION:
                if arrays == 1:
                    stride = width * extra * 4
                    value = payload[row * stride:(row + 1) * stride]
                    rows.append({'position': position, 'token': tokens[row], 'parts': value})
                else:
                    stride = width * 4
                    shared = payload[row * stride:(row + 1) * stride]
                    combined = payload[(nrows + row) * stride:(nrows + row + 1) * stride]
                    rows.append({'position': position, 'token': tokens[row],
                                 'shared': shared, 'combined': combined})
    return raw, rows


def exact_vector_summary(rows, key):
    hashes = [hashlib.sha256(row[key]).hexdigest() for row in rows]
    return {'rows': len(rows), 'sha256': hashes, 'all_bitwise_equal': len(set(hashes)) == 1}


def state_capture(path):
    raw = path.read_bytes()
    view = memoryview(raw)
    offset = 0
    layers = {}
    while offset < len(raw):
        if len(raw) - offset < STATE_HEADER.size:
            raise ValueError(f'{path}: truncated state header at {offset}')
        magic, version, layer, position, recurrent, total, token, slot = STATE_HEADER.unpack_from(raw, offset)
        offset += STATE_HEADER.size
        if magic != b'STGCMT1\0' or version != 1 or position != POSITION or slot != 0 or total < recurrent:
            raise ValueError(f'{path}: invalid state record {(magic, version, layer, position, slot)}')
        size = total * 4
        if len(raw) - offset < size:
            raise ValueError(f'{path}: truncated state payload at {offset}')
        layers.setdefault(layer, []).append((view[offset:offset + size], token))
        offset += size
    if len(layers) != 36 or any(len(rows) != 3 for rows in layers.values()):
        raise ValueError(f'{path}: expected 36 layers x 3 requests, got {len(layers)} layers')
    state_equal = all(len({bytes(row[0]) for row in rows}) == 1 for rows in layers.values())
    return {'raw_sha256': hashlib.sha256(raw).hexdigest(), 'records': sum(map(len, layers.values())),
            'layers': len(layers), 'three_requests_bitwise_equal_at_every_layer': state_equal,
            'layers_equal': sorted(layer for layer, rows in layers.items()
                                   if len({bytes(row[0]) for row in rows}) == 1)}


def input_capture(path):
    raw = path.read_bytes()
    offset = 0
    selected = []
    while offset < len(raw):
        if len(raw) - offset < INPUT_HEADER.size:
            raise ValueError(f'{path}: truncated input header at {offset}')
        magic, version, layer, nrows, reserved, width, pos0, *tokens = INPUT_HEADER.unpack_from(raw, offset)
        offset += INPUT_HEADER.size
        if magic != b'STMOINP1' or version != 1 or layer != 27 or not 0 < nrows <= 8 or \
                reserved != 0 or width != WIDTH:
            raise ValueError(f'{path}: invalid input header')
        size = nrows * width * 4
        if len(raw) - offset < size:
            raise ValueError(f'{path}: truncated input payload at {offset}')
        payload = raw[offset:offset + size]
        offset += size
        for row in range(nrows):
            if pos0 + row == POSITION:
                selected.append((tokens[row], payload[row * WIDTH * 4:(row + 1) * WIDTH * 4]))
    if len(selected) != 3:
        raise ValueError(f'{path}: expected three input rows at {POSITION}, got {len(selected)}')
    hashes = [hashlib.sha256(value).hexdigest() for _, value in selected]
    return {'tokens': [token for token, _ in selected], 'sha256': hashes,
            'all_bitwise_equal': len(set(hashes)) == 1}, [value for _, value in selected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign.resolve().parent
    campaign = json.loads(args.campaign.read_text())
    if campaign.get('status') != 'pass' or campaign.get('binary_sha256') is None:
        raise ValueError('campaign must be a passing paired run with a binary identity')
    result = {'scope': 'one current-source Coder IQ1_M short-short-short sequence pair, generated position 515',
              'seed': campaign['seed'], 'binary_sha256': campaign['binary_sha256'],
              'model_revision': campaign['model_revision'], 'q8_1_selector': campaign['native_cpu_q8_1_dot'],
              'position': POSITION, 'layer': 27, 'expert': EXPERT, 'arms': {}}
    route_state = {}
    for arm in ('adaptive-cap8', 'delayed-control'):
        run = root / arm / 'result'
        dispatch_doc = [json.loads(line) for line in (run / 'all-layer-selected-positions.jsonl').read_text().splitlines()]
        if not dispatch_doc or dispatch_doc[0].get('format') != 'strata-moe-dispatch-v3':
            raise ValueError(f'{arm}: invalid owner trace')
        dispatch = [row for row in dispatch_doc[1:]
                    if row.get('layer') == 27 and row.get('position') == POSITION]
        routes_doc = [json.loads(line) for line in (run / 'verify-moe-routes.jsonl').read_text().splitlines()]
        if not routes_doc or routes_doc[0].get('format') != 'strata-verify-moe-route-v1':
            raise ValueError(f'{arm}: invalid verifier route trace')
        routes = [row for row in routes_doc[1:]
                  if row.get('layer') == 27 and row.get('position') == POSITION]
        input_summary, input_rows = input_capture(run / 'verify-moe-input.bin')
        _, parts = read_rows(run / 'verify-moe-parts.bin', PARTS_HEADER, b'STMPART1', 27)
        _, outputs = read_rows(run / 'verify-moe-output.bin', OUTPUT_HEADER, b'STMOEOUT', 27)
        if not (len(dispatch) == len(routes) == len(parts) == len(outputs) == 3):
            raise ValueError(f'{arm}: expected three paired owner/route/part/output rows')
        for index, (owner, route, part, output) in enumerate(zip(dispatch, routes, parts, outputs)):
            if owner['token_id'] != route['token_id'] or owner['ids'] != route['ids'] or \
                    owner['token_id'] != part['token'] or route['token_id'] != output['token'] or \
                    route['ids'] != routes[0]['ids'] or route['weights'] != routes[0]['weights']:
                raise ValueError(f'{arm} request {index}: owner/route/part identity mismatch')
            if route['token_id'] != input_summary['tokens'][index] or \
                    (owner.get('activation_valid') and
                     struct.pack(f'<{len(owner["activation"])}f', *owner['activation']) != input_rows[index]):
                raise ValueError(f'{arm} request {index}: captured activation does not match verifier input')
        rank = routes[0]['ids'].index(EXPERT)
        expert_vectors = [row['parts'][rank * WIDTH * 4:(rank + 1) * WIDTH * 4] for row in parts]
        expert_hashes = [hashlib.sha256(row).hexdigest() for row in expert_vectors]
        owner_codes = [row['route_kind'][rank] for row in dispatch]
        route_state[arm] = {
            'expert_hashes': expert_hashes, 'owner_codes': owner_codes,
            'activation_hashes': input_summary['sha256'],
            'route_ids': routes[0]['ids'], 'route_weights': routes[0]['weights'],
            'token_ids': [row['token_id'] for row in routes],
        }
        request_doc = json.loads((run / 'requests.json').read_text())['requests']
        ids = [row['ids'] for row in request_doc]
        if len(ids) != 3 or ids[0] != ids[1] or ids[1] != ids[2]:
            raise ValueError(f'{arm}: generated token IDs differ across repeated prompts')
        result['arms'][arm] = {
            'requests': 3, 'generated_tokens_each': len(ids[0]),
            'generated_ids_bitwise_equal_across_requests': True,
            'layer27_route_ids_weights_bitwise_equal': True,
            'layer27_verifier_activation': input_summary,
            'expert_owner_codes': owner_codes,
            'expert129_parts_bitwise_equal_across_requests': len(set(expert_hashes)) == 1,
            'expert129_part_sha256': expert_hashes,
            'shared_output': exact_vector_summary(outputs, 'shared'),
            'combined_output': exact_vector_summary(outputs, 'combined'),
            'committed_state': state_capture(run / 'gdn-commit-state.bin')}
    if route_state['adaptive-cap8']['owner_codes'] != [-1, -1, 0]:
        raise ValueError('adaptive arm did not exercise the expected CPU-to-CUDA owner transition')
    if route_state['delayed-control']['owner_codes'] != [-1, -1, -1]:
        raise ValueError('delayed control did not retain the expected CPU owner')
    for key in ('activation_hashes', 'route_ids', 'route_weights', 'token_ids', 'expert_hashes'):
        if route_state['adaptive-cap8'][key] != route_state['delayed-control'][key]:
            raise ValueError(f'adaptive and delayed {key} differ')
    for field in ('shared_output', 'combined_output'):
        if result['arms']['adaptive-cap8'][field]['sha256'] != \
                result['arms']['delayed-control'][field]['sha256']:
            raise ValueError(f'adaptive and delayed {field} differ')
    for arm in result['arms'].values():
        if not arm['expert129_parts_bitwise_equal_across_requests'] or \
                not arm['shared_output']['all_bitwise_equal'] or not arm['combined_output']['all_bitwise_equal'] or \
                not arm['committed_state']['three_requests_bitwise_equal_at_every_layer']:
            raise ValueError('selected MoE or committed-state vectors differ across repeated requests')
    if result['arms']['adaptive-cap8']['committed_state']['raw_sha256'] != \
            result['arms']['delayed-control']['committed_state']['raw_sha256']:
        raise ValueError('adaptive and delayed committed GDN state captures differ')
    for arm in result['arms'].values():
        arm['cross_arm_equal'] = {
            'activation': True, 'route': True, 'expert129_part': True,
            'shared_output': True, 'combined_output': True, 'committed_state': True,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
