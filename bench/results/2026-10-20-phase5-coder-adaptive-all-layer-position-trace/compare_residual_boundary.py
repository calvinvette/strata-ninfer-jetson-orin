#!/usr/bin/env python3
"""Compare fixed-size verifier residual/hyperconnection boundary records."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIIQQQii')
N = 2560
HC = 4
FIELDS = {
    'after_layer_R': HC * N,
    'after_layer_bo': N,
    'after_layer_inj2': HC,
    'before_next_read_R': HC * N,
    'before_next_read_bo': N,
    'before_next_read_inj2': HC,
    'after_next_read_R': HC * N,
    'after_next_read_xn': HC * N,
}
PAYLOAD = sum(FIELDS.values()) * 4


def parse(path, layer, position):
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f'truncated header at byte {offset}')
        magic, version, rec_layer, rec_pos, n_embd, hc, token, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if (magic, version, rec_layer, rec_pos, n_embd, hc, reserved) != \
                (b'STBNDY1\0', 1, layer, position, N, HC, 0):
            raise ValueError(f'invalid boundary metadata: {magic, version, rec_layer, rec_pos, n_embd, hc, reserved}')
        if len(raw) - offset < PAYLOAD:
            raise ValueError(f'truncated payload at byte {offset}')
        values = {}
        for name, count in FIELDS.items():
            size = count * 4
            data = raw[offset:offset + size]
            floats = struct.unpack(f'<{count}f', data)
            if not all(math.isfinite(value) for value in floats):
                raise ValueError(f'non-finite {name} in {path}')
            values[name] = floats
            offset += size
        records.append({'token': token, 'fields': values})
    return raw, records


def summarize(a, b):
    if len(a) != len(b):
        raise ValueError('field lengths differ')
    differences = [float(y) - float(x) for x, y in zip(a, b)]
    ref_sq = math.fsum(float(x) * float(x) for x in a)
    delta_sq = math.fsum(value * value for value in differences)
    return {
        'values': len(a),
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs_diff': max((abs(value) for value in differences), default=0.0),
        'relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None,
        'left_sha256': hashlib.sha256(struct.pack(f'<{len(a)}f', *a)).hexdigest(),
        'right_sha256': hashlib.sha256(struct.pack(f'<{len(b)}f', *b)).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--layer', type=int, required=True)
    parser.add_argument('--position', type=int, required=True)
    parser.add_argument('--expected-records', type=int, default=3)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.layer < 0 or args.position < 0 or args.expected_records < 2:
        parser.error('layer/position must be non-negative and at least two records are required')
    raw, records = parse(args.run / 'verify-boundary.bin', args.layer, args.position)
    if len(records) != args.expected_records:
        raise ValueError(f'expected {args.expected_records} records, found {len(records)}')
    if len({record['token'] for record in records}) != 1:
        raise ValueError('captured token IDs differ')
    comparisons = {}
    for name in FIELDS:
        transitions = [summarize(records[left]['fields'][name], records[right]['fields'][name])
                       for left, right in zip(range(len(records) - 1), range(1, len(records)))]
        comparisons[name] = {
            'initial_vs_recovery': summarize(records[0]['fields'][name], records[-1]['fields'][name]),
            'request_transitions': transitions,
        }
    result = {
        'scope': 'verifier residual and hyperconnection fields around a selected layer boundary',
        'layer': args.layer,
        'next_layer': args.layer + 1,
        'position': args.position,
        'token_id': records[0]['token'],
        'record_count': len(records),
        'raw_bytes': len(raw),
        'raw_sha256': hashlib.sha256(raw).hexdigest(),
        'fields': comparisons,
        'limits': ['diagnostic verifier values; not the serving session persistent-state store'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'layer': args.layer, 'next_layer': args.layer + 1,
                      'position': args.position,
                      'different_values_initial_recovery': {
                          name: item['initial_vs_recovery']['different_values']
                          for name, item in comparisons.items()},
                      'raw_bytes': len(raw)}, indent=2))


if __name__ == '__main__':
    main()
