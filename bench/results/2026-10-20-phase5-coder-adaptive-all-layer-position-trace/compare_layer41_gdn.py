#!/usr/bin/env python3
"""Compare layer-41 GDN intermediates and raw state at selected positions."""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

GDN_HEADER = struct.Struct('<8sIiiqQQQQQ8i')
STATE_HEADER = struct.Struct('<8sIiqQQii')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')
REQUESTS = ('short-512', 'short-512-intermediate', 'short-512-recovery', 'short-512-continuation-1')
TRANSITIONS = ((0, 1), (1, 2), (2, 3), (0, 2))


def compare(left, right):
    if len(left) != len(right):
        raise ValueError('shape mismatch')
    delta = [float(b) - float(a) for a, b in zip(left, right)]
    denominator = math.fsum(float(a) ** 2 for a in left)
    return {
        'bitwise_equal': left == right,
        'different_values': sum(a != b for a, b in zip(left, right)),
        'max_abs': max(map(abs, delta), default=0.0),
        'relative_l2': math.sqrt(math.fsum(x * x for x in delta) / denominator) if denominator else None,
    }


def read_gdn(path, positions):
    data = path.read_bytes()
    offset = 0
    rows = []
    while offset < len(data):
        header = GDN_HEADER.unpack_from(data, offset)
        offset += GDN_HEADER.size
        magic, version, layer, count, pos, n_embd, conv, v_heads, value_dim, state_floats, *tokens = header
        if magic != b'STGDIAG4' or version != 4 or layer != 41 or count != 1:
            raise ValueError(f'invalid GDN header {header[:10]}')
        counts = (n_embd, conv, conv, v_heads, v_heads, value_dim, value_dim,
                  n_embd, n_embd, n_embd)
        fields = {}
        for name, count_values in zip(FIELDS, counts):
            size = count_values * 4
            raw = data[offset:offset + size]
            offset += size
            if len(raw) != size:
                raise ValueError(f'truncated GDN field {name}')
            fields[name] = struct.unpack(f'<{count_values}f', raw)
        if pos in positions:
            rows.append({'position': pos, 'token': tokens[0],
                         'shape': (n_embd, conv, v_heads, value_dim, state_floats),
                         'fields': fields})
    if offset != len(data) or len(rows) != 4 * len(positions):
        raise ValueError(f'{path}: expected {4 * len(positions)} GDN records, found {len(rows)}')
    return data, rows


def read_states(path, positions):
    data = path.read_bytes()
    offset = 0
    rows = []
    while offset < len(data):
        magic, version, layer, pos, recurrent, total, token, reserved = STATE_HEADER.unpack_from(data, offset)
        offset += STATE_HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != 41 or reserved != 0:
            raise ValueError('invalid raw GDN state header')
        size = total * 4
        payload = data[offset:offset + 2 * size]
        offset += 2 * size
        if len(payload) != 2 * size:
            raise ValueError('truncated raw GDN state')
        if pos in positions:
            rows.append({'position': pos, 'recurrent': recurrent, 'total': total, 'token': token,
                         'pre': payload[:size], 'post': payload[size:]})
    if offset != len(data) or len(rows) != 4 * len(positions):
        raise ValueError(f'{path}: expected {4 * len(positions)} raw state records, found {len(rows)}')
    return data, rows


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


def read_service_hashes(path, positions):
    rows = {position: [] for position in positions}
    pending = None
    for line in path.read_text(errors='replace').splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = line.split('STATE_HASH_GDN ', 1)[1].split()
            continue
        match = re.search(r'ACCEPTED_PREFIX position=(\d+)', line)
        if match and int(match.group(1)) in positions:
            position = int(match.group(1))
            if pending is None:
                raise ValueError('accepted prefix has no preceding GDN hashes')
            rows[position].append(pending)
            pending = None
    for position in positions:
        if len(rows[position]) != 4:
            raise ValueError(f'position {position}: expected four service GDN hash rows, found {len(rows[position])}')
    return rows


def raw_state_differences(left, right, recurrent, total):
    left_rec = struct.unpack(f'<{recurrent}f', left[:recurrent * 4])
    right_rec = struct.unpack(f'<{recurrent}f', right[:recurrent * 4])
    left_conv = struct.unpack(f'<{total - recurrent}f', left[recurrent * 4:])
    right_conv = struct.unpack(f'<{total - recurrent}f', right[recurrent * 4:])
    return sum(a != b for a, b in zip(left_rec, right_rec)), sum(a != b for a, b in zip(left_conv, right_conv))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--positions', type=int, nargs='+', default=[521, 522])
    args = parser.parse_args()
    positions = set(args.positions)
    result = {'scope': 'layer-41 GDN intermediates and raw recurrent state at selected generated positions',
              'layer': 41, 'gdn_ordinal': 31, 'positions': sorted(positions),
              'requests': REQUESTS, 'arms': {}}
    for arm in ('adaptive-cap8', 'delayed-control'):
        run = args.run_dir / arm / 'result'
        raw_gdn, gdn_rows = read_gdn(run / 'verify-gdn.bin', positions)
        raw_state, state_rows = read_states(run / 'gdn-state.bin', positions)
        service_hashes = read_service_hashes(run / 'service.log', positions)
        gdn_by_position = {p: [row for row in gdn_rows if row['position'] == p] for p in positions}
        state_by_position = {p: [row for row in state_rows if row['position'] == p] for p in positions}
        position_results = {}
        for position in sorted(positions):
            gdn = gdn_by_position[position]
            states = state_by_position[position]
            if len(gdn) != 4 or len(states) != 4:
                raise ValueError(f'{arm} position {position}: expected four state and intermediate rows')
            transitions = []
            for left_index, right_index in TRANSITIONS:
                left, right = gdn[left_index], gdn[right_index]
                left_state, right_state = states[left_index], states[right_index]
                if (left['token'] != right['token'] or left['shape'] != right['shape'] or
                        left_state['token'] != left['token'] or right_state['token'] != right['token']):
                    raise ValueError(f'{arm} position {position}: token/state identity mismatch')
                recurrent = left_state['recurrent']
                pre_rec, pre_conv = raw_state_differences(left_state['pre'], right_state['pre'],
                                                          recurrent, left_state['total'])
                post_rec, post_conv = raw_state_differences(left_state['post'], right_state['post'],
                                                            recurrent, left_state['total'])
                transitions.append({
                    'requests': [REQUESTS[left_index], REQUESTS[right_index]],
                    'fields': {name: compare(left['fields'][name], right['fields'][name]) for name in FIELDS},
                    'raw_pre_equal': left_state['pre'] == right_state['pre'],
                    'raw_post_equal': left_state['post'] == right_state['post'],
                    'pre_recurrent_differences': pre_rec,
                    'post_recurrent_differences': post_rec,
                    'pre_convolution_differences': pre_conv,
                    'post_convolution_differences': post_conv,
                })
            checks = []
            for state, hashes in zip(states, service_hashes[position]):
                observed = fnv1a(state['post'])
                checks.append({'token_id': state['token'], 'raw_post_fnv1a': observed,
                               'service_hash': hashes[31], 'matches': observed == hashes[31]})
            if not all(check['matches'] for check in checks):
                raise ValueError(f'{arm} position {position}: raw state/service hash mismatch')
            position_results[str(position)] = {'service_hash_checks': checks, 'transitions': transitions}
        result['arms'][arm] = {
            'gdn_capture_sha256': hashlib.sha256(raw_gdn).hexdigest(),
            'state_capture_sha256': hashlib.sha256(raw_state).hexdigest(),
            'positions': position_results,
        }
    output = args.run_dir / 'layer41-gdn-analysis.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    summary = {}
    for arm, arm_data in result['arms'].items():
        summary[arm] = {}
        for position, data in arm_data['positions'].items():
            summary[arm][position] = [{
                'requests': transition['requests'],
                'first_differing_field': next((name for name, metric in transition['fields'].items()
                                               if not metric['bitwise_equal']), None),
                'raw_pre_equal': transition['raw_pre_equal'],
                'raw_post_equal': transition['raw_post_equal'],
                'pre_recurrent_differences': transition['pre_recurrent_differences'],
                'post_recurrent_differences': transition['post_recurrent_differences'],
                'pre_convolution_differences': transition['pre_convolution_differences'],
                'post_convolution_differences': transition['post_convolution_differences'],
            } for transition in data['transitions']]
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
