#!/usr/bin/env python3
"""Compare raw pre/post GDN state snapshots from the initial/recovery pair."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiqQQii')


def read_records(path, expected_layer):
    data = path.read_bytes()
    records = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated state header in {path} at {offset}')
        magic, version, layer, position, recurrent_floats, state_floats, token, reserved = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != expected_layer or position < 0 or reserved != 0:
            raise ValueError(f'invalid state record header: {magic, version, layer, position, recurrent_floats, state_floats, token, reserved}')
        if not 0 < recurrent_floats <= state_floats:
            raise ValueError(f'invalid recurrent/total state sizes: {recurrent_floats}/{state_floats}')
        nbytes = state_floats * 4
        if len(data) - offset < 2 * nbytes:
            raise ValueError(f'truncated pre/post state payload in {path} at {offset}')
        pre_raw = data[offset:offset + nbytes]
        offset += nbytes
        post_raw = data[offset:offset + nbytes]
        offset += nbytes
        pre = struct.unpack(f'<{state_floats}f', pre_raw)
        post = struct.unpack(f'<{state_floats}f', post_raw)
        records.append({'layer': layer, 'position': position, 'token': token,
                        'recurrent_floats': recurrent_floats, 'state_floats': state_floats,
                        'pre': pre, 'post': post})
    if len(records) < 2:
        raise ValueError(f'expected at least initial and recovery records, found {len(records)} records')
    return records


def summarize(a, b):
    if len(a) != len(b):
        raise ValueError('state comparison shapes differ')
    if any(not math.isfinite(x) for x in a + b):
        raise ValueError('state contains a non-finite value')
    delta_sq = math.fsum((float(y) - float(x)) ** 2 for x, y in zip(a, b))
    ref_sq = math.fsum(float(x) ** 2 for x in a)
    return {
        'values': len(a),
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs_diff': max((abs(float(y) - float(x)) for x, y in zip(a, b)), default=0.0),
        'relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None,
        'initial_f32_sha256': hashlib.sha256(struct.pack(f'<{len(a)}f', *a)).hexdigest(),
        'recovery_f32_sha256': hashlib.sha256(struct.pack(f'<{len(b)}f', *b)).hexdigest(),
    }


def split_summary(a, b, recurrent_floats):
    return {
        'recurrent_matrix': summarize(a[:recurrent_floats], b[:recurrent_floats]),
        'convolution_history': summarize(a[recurrent_floats:], b[recurrent_floats:]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dump', type=Path, required=True,
                        help='raw pre/post records retained outside the repository')
    parser.add_argument('--layer', type=int, default=26, help='GDN model layer (default: 26)')
    parser.add_argument('--requests-json', type=Path,
                        help='request metadata used to verify every expected position record; auto-detected beside the dump')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.layer < 0:
        parser.error('--layer must be non-negative')
    records = read_records(args.state_dump, args.layer)
    requests_path = args.requests_json or args.state_dump.parent / 'requests.json'
    api_requests = (json.loads(requests_path.read_text())['requests']
                    if requests_path.is_file() else None)
    grouped = {}
    for record in records:
        grouped.setdefault(record['position'], []).append(record)
    if any(len(pair) not in (2, 3) for pair in grouped.values()):
        raise ValueError('each selected position must have two or three ordered request records')
    if api_requests is None and any(len(pair) == 3 for pair in grouped.values()):
        raise ValueError('three-record captures need requests.json (use --requests-json) to verify the recovery row')
    if api_requests is not None:
        for position, pair in grouped.items():
            expected = sum(position < request['prompt_tokens'] + len(request['ids'])
                           for request in api_requests)
            if len(pair) != expected:
                raise ValueError(f'position {position}: found {len(pair)} records; expected {expected} '
                                 'from requests.json, so initial/recovery cannot be paired safely')
    comparisons = {}
    for position, pair in sorted(grouped.items()):
        initial, recovery = pair[0], pair[-1]
        for key in ('layer', 'position', 'token', 'recurrent_floats', 'state_floats'):
            if initial[key] != recovery[key]:
                raise ValueError(f'initial/recovery state record metadata differs for {key} at position {position}')
        recurrent = initial['recurrent_floats']
        comparison = {
            'token_id': initial['token'],
            'request_record_count': len(pair),
            'captured_requests': ([request['name'] for request in api_requests
                                   if position < request['prompt_tokens'] + len(request['ids'])]
                                  if api_requests is not None else ['initial', 'recovery']),
            'initial_vs_recovery_pre_state': split_summary(initial['pre'], recovery['pre'], recurrent),
            'initial_vs_recovery_post_state': split_summary(initial['post'], recovery['post'], recurrent),
        }
        if len(pair) == 3:
            transitions = []
            for left, right in ((0, 1), (1, 2)):
                a, b = pair[left], pair[right]
                if a['token'] != b['token']:
                    raise ValueError(f'request token differs at position {position}')
                transitions.append({
                    'request_pair': [left, right],
                    'pre_state': split_summary(a['pre'], b['pre'], recurrent),
                    'post_state': split_summary(a['post'], b['post'], recurrent),
                })
            comparison['request_transitions'] = transitions
        comparisons[str(position)] = comparison
    if len(comparisons) == 1:
        only = next(iter(comparisons.values()))
    else:
        only = {}
    recurrent = records[0]['recurrent_floats']
    result = {
        'scope': f'same-service layer-{args.layer} GDN verifier state immediately before and after selected token positions',
        'positions': [int(position) for position in sorted(comparisons, key=int)],
        'token_id': only.get('token_id'),
        'state_floats': records[0]['state_floats'],
        'recurrent_floats': recurrent,
        'convolution_history_floats': records[0]['state_floats'] - recurrent,
        'raw_state_dump_bytes': args.state_dump.stat().st_size,
        'raw_state_dump_sha256': hashlib.sha256(args.state_dump.read_bytes()).hexdigest(),
        'position_comparisons': comparisons,
        'interpretation_limit': 'selected positions localize a boundary only; they do not establish the cause or values at unselected positions',
    }
    if only:
        pair = grouped[int(next(iter(comparisons)))]
        initial, recovery = pair[0], pair[-1]
        result['initial_vs_recovery_pre_state'] = only['initial_vs_recovery_pre_state']
        result['initial_vs_recovery_post_state'] = only['initial_vs_recovery_post_state']
        result['initial_request_pre_to_post'] = split_summary(initial['pre'], initial['post'], recurrent)
        result['recovery_request_pre_to_post'] = split_summary(recovery['pre'], recovery['post'], recurrent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('positions', 'state_floats', 'recurrent_floats',
                                                    'raw_state_dump_bytes', 'raw_state_dump_sha256',
                                                    'position_comparisons')}, indent=2))


if __name__ == '__main__':
    main()
