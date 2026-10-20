#!/usr/bin/env python3
"""Compare committed layer-specific GDN states across initial/long/recovery requests."""
import argparse
from array import array
from collections import defaultdict
import hashlib
import json
import re
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiqQQii')


def read_records(path, expected_layer):
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError('truncated committed GDN header')
        magic, version, layer, position, recurrent, total, token, slot = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STGCMT1\0' or version != 1 or layer != expected_layer or total < recurrent:
            raise ValueError(f'invalid committed GDN record: {magic, version, layer, position, recurrent, total}')
        size = total * 4
        if len(raw) - offset < size:
            raise ValueError('truncated committed GDN payload')
        values = array('f')
        values.frombytes(raw[offset:offset + size])
        offset += size
        records.append({'position': position, 'recurrent': recurrent, 'token': token, 'slot': slot, 'state': values})
    return raw, records


def summarize(a, b):
    if len(a) != len(b):
        raise ValueError('state shapes differ')
    different = 0
    max_abs = 0.0
    delta_sq = ref_sq = 0.0
    for x, y in zip(a, b):
        delta = float(y) - float(x)
        different += x != y
        max_abs = max(max_abs, abs(delta))
        delta_sq += delta * delta
        ref_sq += float(x) * float(x)
    return {'values': len(a), 'different_values': different, 'max_abs_diff': max_abs,
            'relative_l2': (delta_sq / ref_sq) ** 0.5 if ref_sq else None}


def split(a, b, recurrent):
    return {'recurrent_matrix': summarize(a[:recurrent], b[:recurrent]),
            'convolution_history': summarize(a[recurrent:], b[recurrent:])}


def read_service_gdn_hashes(path):
    pattern = re.compile(r'ACCEPTED_PREFIX position=(\d+)')
    pending = None
    result = defaultdict(list)
    for line in path.read_text().splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = [value.lower() for value in line.split('STATE_HASH_GDN ', 1)[1].split()]
            continue
        match = pattern.search(line)
        if match is not None:
            if pending is None:
                raise ValueError('accepted-prefix service row has no preceding per-GDN hashes')
            result[int(match.group(1))].append(pending)
            pending = None
    return result


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value ^= byte
        value = (value * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


def read_verifier_pre_states(path, expected_layer):
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError('truncated verifier GDN header')
        magic, version, layer, position, recurrent, total, token, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != expected_layer or reserved != 0:
            raise ValueError('invalid verifier GDN state record')
        size = total * 4
        if total < recurrent or len(raw) - offset < size * 2:
            raise ValueError('truncated verifier GDN state payload')
        pre = array('f')
        pre.frombytes(raw[offset:offset + size])
        offset += size * 2
        records.append({'position': position, 'token': token, 'recurrent': recurrent, 'pre': pre})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dump', type=Path, required=True)
    parser.add_argument('--layer', type=int, required=True)
    parser.add_argument('--verifier-state-dump', type=Path,
                        help='optional earlier STGSTAT1 pre/post capture for exact boundary cross-check')
    parser.add_argument('--service-log', type=Path,
                        help='optional accepted-prefix log for checking raw GDN bytes against per-layer hashes')
    parser.add_argument('--gdn-ordinal', type=int,
                        help='global GDN ordinal represented by this layer-specific capture')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw, records = read_records(args.state_dump, args.layer)
    by_position = {}
    for record in records:
        by_position.setdefault(record['position'], []).append(record)
    results = []
    for position, group in sorted(by_position.items()):
        if len(group) < 2:
            raise ValueError(f'position {position} has fewer than initial/recovery records: {len(group)}')
        # The one-service runner sends short, long, then short-recovery prompts.
        # Keep the middle observation but pair the first and final short requests.
        first, last = group[0], group[-1]
        if first['recurrent'] != last['recurrent'] or len(first['state']) != len(last['state']):
            raise ValueError(f'state dimensions differ at position {position}')
        results.append({
            'position': position,
            'record_count': len(group),
            'first_and_recovery_token_ids': [first['token'], last['token']],
            'first_and_recovery_slots': [first['slot'], last['slot']],
            'initial_vs_recovery': split(first['state'], last['state'], first['recurrent']),
            'initial_sha256': hashlib.sha256(first['state'].tobytes()).hexdigest(),
            'recovery_sha256': hashlib.sha256(last['state'].tobytes()).hexdigest(),
            'long_request_sha256': hashlib.sha256(group[1]['state'].tobytes()).hexdigest() if len(group) > 2 else None,
        })
    summary = {
        'layer': args.layer,
        'raw_bytes': len(raw),
        'raw_sha256': hashlib.sha256(raw).hexdigest(),
        'records': len(records),
        'positions': results,
        'first_differing_accepted_endpoint': next((item['position'] for item in results
                                                    if item['initial_vs_recovery']['recurrent_matrix']['different_values'] or
                                                    item['initial_vs_recovery']['convolution_history']['different_values']), None),
        'interpretation_limit': 'records show committed state at selected accepted-prefix endpoints; differing records locate a boundary but do not identify the operation responsible',
    }
    if args.verifier_state_dump is not None:
        verifier = read_verifier_pre_states(args.verifier_state_dump, args.layer)
        at_510 = by_position.get(510, [])
        if len(verifier) != 2 or len(at_510) < 2:
            raise ValueError('expected two verifier snapshots and initial/recovery commit records at position 510')
        pairs = ((verifier[0]['pre'], at_510[0]['state']), (verifier[1]['pre'], at_510[-1]['state']))
        exact = [a.tobytes() == b.tobytes() for a, b in pairs]
        summary['verifier_position_511_pre_vs_commit_510'] = {
            'exact_initial_and_recovery_matches': exact,
            'verifier_pre_sha256': [hashlib.sha256(a.tobytes()).hexdigest() for a, _ in pairs],
            'commit_state_sha256': [hashlib.sha256(b.tobytes()).hexdigest() for _, b in pairs],
        }
        if not all(exact):
            raise ValueError('position-510 commit does not match the earlier position-511 verifier pre-state')
    if (args.service_log is None) != (args.gdn_ordinal is None):
        parser.error('--service-log and --gdn-ordinal must be supplied together')
    if args.gdn_ordinal is not None:
        service = read_service_gdn_hashes(args.service_log)
        checks = []
        for position, group in sorted(by_position.items()):
            service_rows = service.get(position, [])
            if len(service_rows) != len(group):
                raise ValueError(f'position {position}: {len(group)} raw records but {len(service_rows)} service hashes')
            for record, hashes in zip(group, service_rows):
                if not 0 <= args.gdn_ordinal < len(hashes):
                    raise ValueError(f'GDN ordinal {args.gdn_ordinal} out of range at position {position}')
                observed = fnv1a(record['state'].tobytes())
                expected = hashes[args.gdn_ordinal]
                checks.append({'position': position, 'raw_hash': observed,
                               'service_hash': expected, 'matches': observed == expected})
        if not all(row['matches'] for row in checks):
            raise ValueError('raw committed state does not match accepted-prefix service hashes')
        summary['service_hash_crosscheck'] = {
            'gdn_ordinal': args.gdn_ordinal, 'records': len(checks),
            'all_match': True, 'checks': checks,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
