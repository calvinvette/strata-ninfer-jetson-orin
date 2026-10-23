#!/usr/bin/env python3
"""Join long-chain owner, verifier-row and GDN-state captures at position 515."""
from array import array
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT / 'result/all-layer-selected-positions.jsonl'
REQUESTS = OUT / 'result/requests.json'
SUPERVISOR = OUT / 'supervisor/result.json'
RAW_ADAPTIVE = ROOT / 'bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/adaptive-cap8/result'
RAW_DELAYED = ROOT / 'bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/delayed-control-recapture/result'
PREVIOUS_OWNER_PAIR = ROOT / 'bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer21-position515-open-response-direct-division-128pos/adaptive-cap8/result'
ORACLE_ACTIVATION = ROOT / 'bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/operator-oracle-open-response/layer21-expert132/activation.f32'
POSITION = 515
LAYER = 21
GDN_LAYER = 22
GDN_ORDINAL = 17
EMBD = 2560


def sha(data):
    return hashlib.sha256(data).hexdigest()


def vector_summary(a, b):
    if len(a) != len(b):
        raise ValueError('vector shape mismatch')
    changed = 0
    max_abs = 0.0
    delta_sq = ref_sq = 0.0
    for x, y in zip(a, b):
        delta = float(y) - float(x)
        changed += x != y
        max_abs = max(max_abs, abs(delta))
        delta_sq += delta * delta
        ref_sq += float(x) * float(x)
    return {'values': len(a), 'different_values': changed, 'max_abs_diff': max_abs,
            'relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None}


def read_capture():
    lines = OWNER.read_text().splitlines()
    header = json.loads(lines[0])
    if header.get('format') != 'strata-moe-dispatch-v3':
        raise ValueError('unexpected all-layer capture format')
    rows = [json.loads(line) for line in lines[1:]]
    rows = [row for row in rows if row.get('position') == POSITION]
    grouped = {}
    for row in rows:
        grouped.setdefault(row['layer'], []).append(row)
    if set(grouped) != set(range(48)) or any(len(grouped[i]) != 3 for i in range(48)):
        raise ValueError('expected three requests × all 48 layers at position 515')
    return grouped


def read_verify_rows(base, kind, selected_layer, selected_position, expected=3):
    route_rows = [json.loads(line) for line in (base / 'verify-moe-routes.jsonl').read_text().splitlines()]
    if route_rows[0].get('format') != 'strata-verify-moe-route-v1':
        raise ValueError('unexpected verifier route format')
    routes = [r for r in route_rows[1:] if r['layer'] == selected_layer and r['position'] == selected_position]
    if len(routes) != expected:
        raise ValueError(f'expected {expected} verifier route rows')

    path = base / f'verify-moe-{kind}.bin'
    data = path.read_bytes()
    header = struct.Struct('<8sIIIIQq8i')
    rows = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < header.size:
            raise ValueError(f'truncated {kind} header')
        magic, version, layer, count, k, n_embd, pos0, *tokens = header.unpack_from(data, offset)
        offset += header.size
        if version != 1 or layer != selected_layer or n_embd != EMBD or not 0 < count <= 8:
            raise ValueError(f'invalid {kind} record header')
        width = k * n_embd if kind == 'parts' else n_embd
        nbytes = count * width * 4
        if len(data) - offset < nbytes * (2 if kind == 'output' else 1):
            raise ValueError(f'truncated {kind} payload')
        first = struct.unpack_from(f'<{count * width}f', data, offset)
        offset += nbytes
        second = None
        if kind == 'output':
            second = struct.unpack_from(f'<{count * width}f', data, offset)
            offset += nbytes
        for row in range(count):
            pos = pos0 + row
            if pos != selected_position:
                continue
            begin = row * width
            record = {'position': pos, 'token_id': tokens[row]}
            if kind == 'parts':
                record['parts'] = first[begin:begin + width]
                record['k'] = k
            else:
                record['shared'] = first[begin:begin + width]
                record['combined'] = second[begin:begin + width]
            rows.append(record)
    if len(rows) != expected or [r['token_id'] for r in rows] != [r['token_id'] for r in routes]:
        raise ValueError(f'{kind} token/row count does not match verifier routes')
    return routes, rows


def read_state_records(path):
    data = path.read_bytes()
    head = struct.Struct('<8sIiqQQii')
    records = []
    offset = 0
    while offset < len(data):
        magic, version, layer, position, recurrent, total, token, slot = head.unpack_from(data, offset)
        offset += head.size
        if magic != b'STGCMT1\0' or version != 1 or layer != GDN_LAYER or total < recurrent:
            raise ValueError('invalid committed GDN record')
        size = total * 4
        raw = data[offset:offset + size]
        if len(raw) != size:
            raise ValueError('truncated committed GDN state')
        values = array('f'); values.frombytes(raw); offset += size
        if position == POSITION:
            records.append({'token_id': token, 'state': values, 'raw': raw, 'recurrent': recurrent})
    if len(records) != 3:
        raise ValueError('expected three committed layer-22 state records at position 515')
    return records


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value ^= byte
        value = (value * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


def service_hashes(path):
    results = []
    pending = None
    for line in path.read_text().splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = line.split('STATE_HASH_GDN ', 1)[1].split()
        elif 'ACCEPTED_PREFIX position=515 ' in line:
            if pending is None:
                raise ValueError('accepted position 515 lacks GDN hash row')
            results.append(pending)
            pending = None
    if len(results) != 3 or any(len(row) <= GDN_ORDINAL for row in results):
        raise ValueError('expected three accepted-prefix GDN hash rows at position 515')
    return [row[GDN_ORDINAL].lower() for row in results]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path,
                        help='optionally verify the captured binary SHA256 against this executable')
    args = parser.parse_args()
    capture = read_capture()
    request_rows = json.loads(REQUESTS.read_text())['requests']
    if [row['name'] for row in request_rows] != ['short-512', 'short-512-intermediate', 'short-512-recovery'] or \
            any(len(row['ids']) != 256 for row in request_rows):
        raise ValueError('unexpected long-chain request sequence')
    supervisor = json.loads(SUPERVISOR.read_text())
    if supervisor.get('status') != 'pass':
        raise ValueError('owner-capture supervisor did not pass')

    l21 = capture[LAYER]
    expert = 132
    ranks = [row['ids'].index(expert) for row in l21]
    if any(rank != 9 for rank in ranks):
        raise ValueError(f'expert 132 changed route rank: {ranks}')
    if any(row['token_id'] != 16661 for row in l21):
        raise ValueError('position-515 token IDs differ across owner capture')
    if not (l21[0]['ids'] == l21[1]['ids'] == l21[2]['ids']):
        raise ValueError('layer-21 expert IDs changed at position 515')
    if not all(row.get('activation_valid') for row in l21) or not (l21[0]['activation'] == l21[1]['activation'] == l21[2]['activation']):
        raise ValueError('layer-21 activation missing or changed')
    activation_bytes = struct.pack(f'<{EMBD}f', *l21[0]['activation'])
    activation_sha = sha(activation_bytes)
    oracle_sha = sha(ORACLE_ACTIVATION.read_bytes())
    if activation_sha != oracle_sha:
        raise ValueError('captured layer-21 activation differs from independent-oracle input')

    owner_rows = {}
    for request_index, row in enumerate(l21):
        owner_rows[str(request_index)] = row['route_kind']
    if [row['route_kind'][9] for row in l21] != [-1, 0, 0]:
        raise ValueError('expected expert 132 CPU→GPU ownership across first request transition')

    l22 = capture[GDN_LAYER]
    l22_activation = [row['activation'] for row in l22]
    l22_deltas = {
        'initial_to_intermediate': vector_summary(l22_activation[0], l22_activation[1]),
        'intermediate_to_recovery': vector_summary(l22_activation[1], l22_activation[2]),
        'initial_to_recovery': vector_summary(l22_activation[0], l22_activation[2]),
    }

    routes, parts = read_verify_rows(RAW_ADAPTIVE, 'parts', LAYER, POSITION)
    _, outputs = read_verify_rows(RAW_ADAPTIVE, 'output', LAYER, POSITION)
    for i in range(3):
        if routes[i]['ids'] != l21[i]['ids']:
            raise ValueError('all-layer and verifier route records disagree')
    if not (routes[0]['weights'] == routes[1]['weights'] == routes[2]['weights']):
        raise ValueError('layer-21 verifier router weights changed at position 515')
    row_vectors = [part['parts'][ranks[i] * EMBD:(ranks[i] + 1) * EMBD] for i, part in enumerate(parts)]
    output_vectors = [row['combined'] for row in outputs]
    old_routes, old_parts = read_verify_rows(PREVIOUS_OWNER_PAIR, 'parts', LAYER, POSITION, expected=2)
    if len(old_routes) != 2 or any(row['ids'].index(expert) != 9 for row in old_routes):
        raise ValueError('previous same-input owner capture has an unexpected expert rank')
    old_row_vectors = [part['parts'][9 * EMBD:10 * EMBD] for part in old_parts]
    row_hashes = [sha(struct.pack(f'<{EMBD}f', *row)) for row in row_vectors]
    previous_row_hashes = [sha(struct.pack(f'<{EMBD}f', *row)) for row in old_row_vectors]
    row_repeat_match = [row_hashes[0] == previous_row_hashes[0],
                        row_hashes[1] == previous_row_hashes[1],
                        row_hashes[2] == previous_row_hashes[1]]
    if not all(row_repeat_match):
        raise ValueError('owner-specific expert-132 rows differ from prior same-input capture')
    owner_output = {
        'layer21_expert132_rank': 9,
        'owner_kind_by_request': [row['route_kind'][9] for row in l21],
        'row_deltas': {
            'initial_to_intermediate': vector_summary(row_vectors[0], row_vectors[1]),
            'intermediate_to_recovery': vector_summary(row_vectors[1], row_vectors[2]),
            'initial_to_recovery': vector_summary(row_vectors[0], row_vectors[2]),
        },
        'combined_moe_deltas': {
            'initial_to_intermediate': vector_summary(output_vectors[0], output_vectors[1]),
            'intermediate_to_recovery': vector_summary(output_vectors[1], output_vectors[2]),
            'initial_to_recovery': vector_summary(output_vectors[0], output_vectors[2]),
        },
        'activation_sha256': activation_sha,
        'independent_oracle_activation_sha256': oracle_sha,
        'activation_matches_independent_oracle_input': True,
        'expert132_row_sha256_by_request': row_hashes,
        'repeat_matches_prior_same_input_service_rows': row_repeat_match,
        'prior_capture_cpu_gpu_row_sha256': previous_row_hashes,
        'independent_oracle_report': str(PREVIOUS_OWNER_PAIR.parents[2] / 'operator-oracle-open-response/layer21-expert132/README.md'),
    }

    state = read_state_records(RAW_ADAPTIVE / 'gdn-commit-state.bin')
    hashes = service_hashes(RAW_ADAPTIVE / 'service.log')
    raw_hashes = [fnv1a(row['raw']) for row in state]
    if raw_hashes != hashes:
        raise ValueError('raw committed GDN state does not match service hashes')
    def state_delta(a, b):
        rec = state[a]['recurrent']; rec_b = state[b]['recurrent']
        if rec != rec_b:
            raise ValueError('GDN recurrent sizes differ')
        return {
            'recurrent': vector_summary(state[a]['state'][:rec], state[b]['state'][:rec]),
            'convolution_history': vector_summary(state[a]['state'][rec:], state[b]['state'][rec:]),
        }
    gdn_deltas = {
        'initial_to_intermediate': state_delta(0, 1),
        'intermediate_to_recovery': state_delta(1, 2),
        'initial_to_recovery': state_delta(0, 2),
        'raw_to_service_hash_crosscheck': {'records': 3, 'gdn_ordinal': GDN_ORDINAL, 'all_match': True,
                                           'hashes': raw_hashes},
    }

    # Confirm the owner-capture run followed the same exact adaptive token path
    # as the earlier raw-state run that supplied verifier rows and state.
    raw_requests = json.loads((RAW_ADAPTIVE / 'requests.json').read_text())['requests']
    token_match = [a['ids'] == b['ids'] for a, b in zip(request_rows, raw_requests)]
    if not all(token_match):
        raise ValueError('owner and raw-state captures do not share the same token path')
    campaign = json.loads((RAW_ADAPTIVE.parent.parent / 'campaign.json').read_text())
    if args.binary is not None and sha(args.binary.read_bytes()) != campaign['binary_sha256']:
        raise ValueError('provided executable differs from the raw-state capture identity')

    result = {
        'scope': 'long-chain adaptive ownership and layer-22 raw-state join at Coder IQ1_M model position 515',
        'binary_sha256': campaign['binary_sha256'],
        'binary_verification': ('provided executable SHA256 matched the captured campaign'
                                if args.binary is not None else
                                'captured campaign SHA256 recorded; historical executable not rechecked'),
        'repository_head': campaign['repository_head'],
        'model_repository': campaign['model_repository'],
        'model_revision': campaign['model_revision'],
        'quantization': campaign['quantization'],
        'model_shard_sha256': campaign['model_shard_sha256'],
        'workload_sha256': campaign['prompt_workload_file_sha256'],
        'position': POSITION,
        'requests': [{'name': row['name'], 'prompt_tokens': row['prompt_tokens'], 'generated_tokens': len(row['ids'])}
                     for row in request_rows],
        'owner_capture_token_path_matches_raw_state_run': token_match,
        'layer21_expert132': owner_output,
        'layer22_moe_input_deltas': l22_deltas,
        'layer22_committed_state_deltas': gdn_deltas,
        'layer21_owner_kinds_by_request': owner_rows,
        'interpretation_limits': [
            'the CPU→GPU expert-132 row is a numerically verified contributor for this transition, not a complete explanation of all long-chain drift',
            'intermediate-to-recovery layer-22 state and MoE input still change after layer-21 expert-132 output becomes identical, so other layer/owner transitions contribute',
            'the independent oracle validates this exact activation and owner-specific expert row only; no default or general numerical bound follows',
        ],
    }
    (OUT / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'layer21_rank9_owner': owner_output['owner_kind_by_request'],
                      'activation_sha256': activation_sha,
                      'expert132_relative_l2': owner_output['row_deltas']['initial_to_intermediate']['relative_l2'],
                      'combined_relative_l2': owner_output['combined_moe_deltas']['initial_to_intermediate']['relative_l2'],
                      'layer22_state_relative_l2': gdn_deltas['initial_to_intermediate']['recurrent']['relative_l2'],
                      'layer22_input_relative_l2': l22_deltas['initial_to_intermediate']['relative_l2']}, indent=2))


if __name__ == '__main__':
    main()
