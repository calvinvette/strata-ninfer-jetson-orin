#!/usr/bin/env python3
"""Join three-request layer-26 MoE and GDN-state captures."""
import hashlib
import json
import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PART = struct.Struct('<8sIIIIQq8i')
STATE = struct.Struct('<8sIiqQQii')
REQUESTS = ('short-512', 'short-512-intermediate', 'short-512-recovery')


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


def read_parts(path):
    raw = path.read_bytes()
    rows, offset = [], 0
    while offset < len(raw):
        magic, version, layer, count, k, width, pos0, *tokens = PART.unpack_from(raw, offset)
        offset += PART.size
        if magic != b'STMPART1' or version != 1 or layer != 26 or not 0 < count <= 8:
            raise ValueError(f'invalid expert-parts record in {path}')
        n = count * k * width
        values = struct.unpack_from(f'<{n}f', raw, offset)
        offset += n * 4
        for i in range(count):
            rows.append({'position': pos0 + i, 'token_id': tokens[i], 'k': k, 'width': width,
                         'parts': [values[(i * k + rank) * width:(i * k + rank + 1) * width]
                                   for rank in range(k)]})
    return raw, rows


def read_states(path):
    raw = path.read_bytes()
    rows, offset = [], 0
    while offset < len(raw):
        magic, version, layer, position, recurrent, total, token, reserved = STATE.unpack_from(raw, offset)
        offset += STATE.size
        if magic != b'STGSTAT1' or version != 1 or layer != 26 or reserved != 0 or total < recurrent:
            raise ValueError(f'invalid GDN state record in {path}')
        n = total * 4
        pre, post = raw[offset:offset + n], raw[offset + n:offset + 2 * n]
        if len(post) != n:
            raise ValueError(f'truncated GDN state record in {path}')
        offset += 2 * n
        rows.append({'position': position, 'token_id': token, 'recurrent_floats': recurrent,
                     'state_floats': total, 'pre': pre, 'post': post})
    return raw, rows


def service_hashes(path, position):
    pending = None
    found = []
    pattern = re.compile(r'ACCEPTED_PREFIX position=(\d+)')
    for line in path.read_text(errors='replace').splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = line.split('STATE_HASH_GDN ', 1)[1].split()
            continue
        match = pattern.search(line)
        if match:
            if pending is None:
                raise ValueError('accepted prefix missing its GDN hashes')
            if int(match.group(1)) == position:
                found.append(pending)
            pending = None
    return found


def different(a, b):
    return sum(x != y for x, y in zip(a, b))


def relative_l2(a, b):
    delta = math.fsum((float(y) - float(x)) ** 2 for x, y in zip(a, b))
    ref = math.fsum(float(x) ** 2 for x in a)
    return math.sqrt(delta / ref) if ref else None


def main():
    result = {'scope': 'three-request same-service layer-26 routed MoE and GDN state trace',
              'requests': list(REQUESTS), 'positions': {}}
    for arm in ('delayed-control', 'adaptive-cap8'):
        run = ROOT / arm / 'result'
        routes = [json.loads(line) for line in (run / 'verify-moe-routes.jsonl').read_text().splitlines()][1:]
        routes = [row for row in routes if row['layer'] == 26]
        dispatch = [json.loads(line) for line in (run / 'all-layer-selected-positions.jsonl').read_text().splitlines()][1:]
        parts_raw, parts = read_parts(run / 'verify-moe-parts.bin')
        state_raw, states = read_states(run / 'gdn-state.bin')
        arm_result = {'positions': {}, 'state_position_516': {},
                      'capture_sha256': {'parts': hashlib.sha256(parts_raw).hexdigest(),
                                         'state': hashlib.sha256(state_raw).hexdigest()}}
        for position in (512, 516):
            rr = [row for row in routes if row['position'] == position]
            pp = [row for row in parts if row['position'] == position]
            dd = [row for row in dispatch if row['layer'] == 26 and row['position'] == position]
            if not (len(rr) == len(pp) == len(dd) == 3):
                raise ValueError(f'{arm} position {position}: expected three route, parts and dispatch records')
            if any(r['token_id'] != d['token_id'] or r['ids'] != d['ids'] for r, d in zip(rr, dd)):
                raise ValueError(f'{arm} position {position}: route/dispatch token or IDs mismatch')
            transitions = []
            for i in (0, 1):
                changed_rows = []
                for rank, (a, b) in enumerate(zip(pp[i]['parts'], pp[i + 1]['parts'])):
                    count = different(a, b)
                    if count:
                        changed_rows.append({'rank': rank, 'expert_ids': [rr[i]['ids'][rank], rr[i + 1]['ids'][rank]],
                                             'owner_kinds': [dd[i]['route_kind'][rank], dd[i + 1]['route_kind'][rank]],
                                             'different_output_values': count,
                                             'relative_l2': relative_l2(a, b)})
                transitions.append({
                    'request_pair': list(REQUESTS[i:i + 2]),
                    'token_ids_equal': rr[i]['token_id'] == rr[i + 1]['token_id'],
                    'route_ids_equal': rr[i]['ids'] == rr[i + 1]['ids'],
                    'router_weights_equal': rr[i]['weights'] == rr[i + 1]['weights'],
                    'activation_equal': dd[i]['activation'] == dd[i + 1]['activation'],
                    'owner_difference_ranks': [rank for rank, (a, b) in enumerate(
                        zip(dd[i]['route_kind'], dd[i + 1]['route_kind'])) if a != b],
                    'changed_expert_rows': changed_rows,
                })
            arm_result['positions'][str(position)] = transitions
        selected_states = [row for row in states if row['position'] == 516]
        hashes = service_hashes(run / 'service.log', 516)
        if len(selected_states) != 3 or len(hashes) != 3:
            raise ValueError(f'{arm}: expected three raw and service state records at position 516')
        checked = []
        for row, per_gdn in zip(selected_states, hashes):
            observed = fnv1a(row['post'])
            if len(per_gdn) <= 20 or observed != per_gdn[20]:
                raise ValueError(f'{arm}: raw layer-26 post-state hash does not match GDN ordinal 20')
            checked.append({'token_id': row['token_id'], 'raw_hash': observed,
                            'service_gdn_ordinal_20_hash': per_gdn[20], 'matches': True})
        state_transitions = []
        for i in (0, 1):
            a, b = selected_states[i], selected_states[i + 1]
            recurrent = a['recurrent_floats']
            a_pre = struct.unpack(f'<{a["state_floats"]}f', a['pre'])
            b_pre = struct.unpack(f'<{b["state_floats"]}f', b['pre'])
            a_post = struct.unpack(f'<{a["state_floats"]}f', a['post'])
            b_post = struct.unpack(f'<{b["state_floats"]}f', b['post'])
            state_transitions.append({
                'request_pair': list(REQUESTS[i:i + 2]),
                'token_ids_equal': a['token_id'] == b['token_id'],
                'pre_state_equal': a['pre'] == b['pre'],
                'post_state_equal': a['post'] == b['post'],
                'pre_state_different_float_values': different(a_pre, b_pre),
                'post_state_different_float_values': different(a_post, b_post),
                'post_recurrent_different_values': different(a_post[:recurrent], b_post[:recurrent]),
                'post_convolution_different_values': different(a_post[recurrent:], b_post[recurrent:]),
            })
        arm_result['state_position_516'] = {'transitions': state_transitions,
                                             'service_hash_crosscheck': checked}
        result['positions'][arm] = arm_result
    output = ROOT / 'layer26-capture-analysis.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({arm: {
        'position_512_transitions': result['positions'][arm]['positions']['512'],
        'position_516_transitions': result['positions'][arm]['positions']['516'],
        'state_position_516': result['positions'][arm]['state_position_516']['transitions'],
    } for arm in result['positions']}, indent=2))


if __name__ == '__main__':
    main()
