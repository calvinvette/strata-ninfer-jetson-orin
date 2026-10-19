#!/usr/bin/env python3
"""Compare selected raw GDN commit states across delayed and adaptive service runs."""
import argparse
import hashlib
import json
from pathlib import Path

from compare_gdn_commit_state_trace import read_records, split


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delayed-state-dump', type=Path, required=True)
    parser.add_argument('--adaptive-state-dump', type=Path, required=True)
    parser.add_argument('--layer', type=int, required=True)
    parser.add_argument('--position', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    delayed_raw, delayed_records = read_records(args.delayed_state_dump, args.layer)
    adaptive_raw, adaptive_records = read_records(args.adaptive_state_dump, args.layer)

    def select(records, arm):
        rows = [row for row in records if row['position'] == args.position]
        if len(rows) < 2:
            raise ValueError(f'{arm} has fewer than two records at {args.position}')
        first, last = rows[0], rows[-1]
        if first['recurrent'] != last['recurrent'] or len(first['state']) != len(last['state']):
            raise ValueError(f'{arm} state dimensions differ')
        return rows, first, last

    delayed_rows, delayed_initial, delayed_recovery = select(delayed_records, 'delayed')
    adaptive_rows, adaptive_initial, adaptive_recovery = select(adaptive_records, 'adaptive')
    if delayed_initial['recurrent'] != adaptive_initial['recurrent'] or len(delayed_initial['state']) != len(adaptive_initial['state']):
        raise ValueError('delayed/adaptive state dimensions differ')

    result = {
        'layer': args.layer,
        'position': args.position,
        'delayed_capture_sha256': hashlib.sha256(delayed_raw).hexdigest(),
        'adaptive_capture_sha256': hashlib.sha256(adaptive_raw).hexdigest(),
        'delayed_record_count_at_position': len(delayed_rows),
        'adaptive_record_count_at_position': len(adaptive_rows),
        'delayed_initial_vs_recovery': split(delayed_initial['state'], delayed_recovery['state'], delayed_initial['recurrent']),
        'adaptive_initial_vs_recovery': split(adaptive_initial['state'], adaptive_recovery['state'], adaptive_initial['recurrent']),
        'delayed_initial_vs_adaptive_initial': split(delayed_initial['state'], adaptive_initial['state'], delayed_initial['recurrent']),
        'delayed_recovery_vs_adaptive_recovery': split(delayed_recovery['state'], adaptive_recovery['state'], delayed_initial['recurrent']),
        'record_tokens': {
            'delayed': [row['token'] for row in delayed_rows],
            'adaptive': [row['token'] for row in adaptive_rows],
        },
        'interpretation_limit': 'these records compare committed states at one accepted endpoint; they do not identify the operation that caused any state difference',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
