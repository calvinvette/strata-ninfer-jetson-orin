#!/usr/bin/env python3
"""Compare three short-request layer-26 GDN states and service hashes."""
from array import array
from collections import defaultdict
import argparse
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = struct.Struct('<8sIiqQQii')
REQUESTS = ('short-512', 'short-512-intermediate', 'short-512-recovery')


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


def read_states(path, expected_layer):
    raw = path.read_bytes()
    rows, offset = [], 0
    while offset < len(raw):
        magic, version, layer, position, recurrent, total, token, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != expected_layer or reserved != 0 or total < recurrent:
            raise ValueError('invalid layer-26 verifier GDN state header')
        size = total * 4
        pre = array('f'); pre.frombytes(raw[offset:offset + size])
        post = array('f'); post.frombytes(raw[offset + size:offset + 2 * size])
        if len(post) != total:
            raise ValueError('truncated GDN state payload')
        offset += 2 * size
        rows.append({'position': position, 'token': token, 'recurrent': recurrent,
                     'pre': pre, 'post': post, 'pre_raw': raw[offset - 2 * size:offset - size],
                     'post_raw': raw[offset - size:offset]})
    return raw, rows


def service_hashes(path):
    result = defaultdict(list)
    pending = None
    pattern = re.compile(r'ACCEPTED_PREFIX position=(\d+)')
    for line in path.read_text(errors='replace').splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = line.split('STATE_HASH_GDN ', 1)[1].split()
            continue
        match = pattern.search(line)
        if match:
            if pending is None:
                raise ValueError('accepted prefix is missing GDN hashes')
            result[int(match.group(1))].append(pending)
            pending = None
    return result


def diff_count(a, b):
    return sum(x != y for x, y in zip(a, b))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=ROOT,
                        help='paired run containing delayed-control and adaptive-cap8 directories')
    parser.add_argument('--layer', type=int, default=32)
    parser.add_argument('--gdn-ordinal', type=int, default=24)
    args = parser.parse_args()
    output = {'scope': f'raw layer-{args.layer} GDN state across same-service request transitions',
              'layer': args.layer, 'gdn_ordinal': args.gdn_ordinal, 'arms': {}}
    for arm in ('delayed-control', 'adaptive-cap8'):
        run = args.run_dir / arm / 'result'
        raw, records = read_states(run / 'gdn-state.bin', args.layer)
        hashes = service_hashes(run / 'service.log')
        grouped = defaultdict(list)
        for row in records:
            grouped[row['position']].append(row)
        arm_output = {'raw_sha256': __import__('hashlib').sha256(raw).hexdigest(), 'positions': {}}
        for position in sorted(grouped):
            group = grouped[position]
            service = hashes[position]
            if len(group) != 3 or len(service) != 3:
                raise ValueError(f'{arm} position {position}: expected three raw states and service hashes')
            checks = []
            for state, per_gdn in zip(group, service):
                observed = fnv1a(state['post_raw'])
                if len(per_gdn) <= args.gdn_ordinal or observed != per_gdn[args.gdn_ordinal]:
                    raise ValueError(f'{arm} position {position}: raw post-state hash mismatch at GDN ordinal {args.gdn_ordinal}')
                checks.append({'token_id': state['token'], 'raw_hash': observed,
                               'service_hash': per_gdn[args.gdn_ordinal], 'matches': True})
            transitions = []
            for i in (0, 1):
                a, b = group[i], group[i + 1]
                transitions.append({
                    'requests': list(REQUESTS[i:i + 2]),
                    'token_ids_equal': a['token'] == b['token'],
                    'pre_state_equal': a['pre_raw'] == b['pre_raw'],
                    'post_state_equal': a['post_raw'] == b['post_raw'],
                    'pre_recurrent_differences': diff_count(a['pre'][:a['recurrent']], b['pre'][:b['recurrent']]),
                    'pre_convolution_differences': diff_count(a['pre'][a['recurrent']:], b['pre'][b['recurrent']:]),
                    'post_recurrent_differences': diff_count(a['post'][:a['recurrent']], b['post'][:b['recurrent']]),
                    'post_convolution_differences': diff_count(a['post'][a['recurrent']:], b['post'][b['recurrent']:]),
                })
            arm_output['positions'][str(position)] = {'transitions': transitions,
                                                       'service_hash_checks': checks}
        output['arms'][arm] = arm_output
    path = ROOT / 'state-prefix-analysis.json'
    path.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({arm: {
        position: [
            (row['pre_state_equal'], row['post_state_equal'],
             row['post_recurrent_differences'], row['post_convolution_differences'])
            for row in data['transitions']]
        for position, data in rows['positions'].items()
    } for arm, rows in output['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
