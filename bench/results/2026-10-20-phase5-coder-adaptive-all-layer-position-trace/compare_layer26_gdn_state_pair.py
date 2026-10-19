#!/usr/bin/env python3
"""Compare raw pre/post GDN state snapshots from the initial/recovery pair."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiqQQii')


def read_records(path):
    data = path.read_bytes()
    records = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated state header in {path} at {offset}')
        magic, version, layer, position, recurrent_floats, state_floats, token, reserved = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != 26 or position != 511 or reserved != 0:
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
    if len(records) != 2:
        raise ValueError(f'expected initial and recovery state records, found {len(records)}')
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
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    initial, recovery = read_records(args.state_dump)
    for key in ('layer', 'position', 'token', 'recurrent_floats', 'state_floats'):
        if initial[key] != recovery[key]:
            raise ValueError(f'initial/recovery state record metadata differs for {key}')
    recurrent = initial['recurrent_floats']
    result = {
        'scope': 'same-service layer-26 GDN state immediately before and after verifier position 511',
        'token_id': initial['token'],
        'state_floats': initial['state_floats'],
        'recurrent_floats': recurrent,
        'convolution_history_floats': initial['state_floats'] - recurrent,
        'raw_state_dump_bytes': args.state_dump.stat().st_size,
        'raw_state_dump_sha256': hashlib.sha256(args.state_dump.read_bytes()).hexdigest(),
        'initial_vs_recovery_pre_state': split_summary(initial['pre'], recovery['pre'], recurrent),
        'initial_vs_recovery_post_state': split_summary(initial['post'], recovery['post'], recurrent),
        'initial_request_pre_to_post': split_summary(initial['pre'], initial['post'], recurrent),
        'recovery_request_pre_to_post': split_summary(recovery['pre'], recovery['post'], recurrent),
        'interpretation_limit': 'two paired states at one position establish this boundary only; they do not identify when earlier tokens first changed the persistent state',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('token_id', 'state_floats', 'recurrent_floats',
                                                    'raw_state_dump_bytes', 'raw_state_dump_sha256',
                                                    'initial_vs_recovery_pre_state', 'initial_vs_recovery_post_state')}, indent=2))


if __name__ == '__main__':
    main()
