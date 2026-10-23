#!/usr/bin/env python3
"""Find accepted endpoints where same-service initial/recovery GDN hashes differ."""
import argparse
import json
import re
from pathlib import Path

ACCEPTED = re.compile(r'ACCEPTED_PREFIX position=(\d+).*?tokens=(\d+)')


def read_rows(path):
    rows = []
    pending = None
    for line in path.read_text(errors='replace').splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = [value.lower() for value in line.split('STATE_HASH_GDN ', 1)[1].split()]
            continue
        match = ACCEPTED.search(line)
        if match:
            if pending is None:
                raise ValueError(f'{path}: accepted endpoint lacks preceding per-GDN hashes')
            rows.append({'position': int(match.group(1)), 'token_id': int(match.group(2)),
                         'gdn_hashes': pending})
            pending = None
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service-log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--qsa-interval', type=int, default=4)
    parser.add_argument('--stop-at-token-divergence', action='store_true',
                        help='report only the shared accepted-token prefix and stop at its first mismatch')
    args = parser.parse_args()
    if args.qsa_interval <= 0:
        parser.error('--qsa-interval must be positive')

    grouped = {}
    for row in read_rows(args.service_log):
        grouped.setdefault(row['position'], []).append(row)
    comparisons = []
    token_divergence = None
    for position, pair in sorted(grouped.items()):
        if len(pair) != 2:
            continue
        first, recovery = pair
        if first['token_id'] != recovery['token_id']:
            if args.stop_at_token_divergence:
                token_divergence = {'position': position, 'initial_token_id': first['token_id'],
                                    'recovery_token_id': recovery['token_id']}
                break
            raise ValueError(f'initial/recovery token IDs differ at accepted position {position}')
        if len(first['gdn_hashes']) != len(recovery['gdn_hashes']):
            raise ValueError(f'GDN hash counts differ at accepted position {position}')
        ordinals = [ordinal for ordinal, (a, b) in enumerate(zip(first['gdn_hashes'], recovery['gdn_hashes']))
                    if a != b]
        comparisons.append({'position': position, 'token_id': first['token_id'],
                            'different_gdn_ordinals': ordinals,
                            'different_model_layers': [ordinal + ordinal // (args.qsa_interval - 1)
                                                       for ordinal in ordinals],
                            'different_gdn_count': len(ordinals),
                            'gdn_layer_count': len(first['gdn_hashes'])})
    if not comparisons and token_divergence is None:
        raise ValueError('no accepted positions had both initial and recovery hashes')
    result = {
        'scope': 'per-GDN 64-bit service hashes at accepted endpoints present twice in one service log',
        'qsa_interval': args.qsa_interval,
        'first_differing_position': next((row['position'] for row in comparisons
                                          if row['different_gdn_ordinals']), None),
        'token_divergence': token_divergence,
        'comparison_stopped_at_token_divergence': token_divergence is not None,
        'positions': comparisons,
        'interpretation_limit': ('hashes after the first token mismatch are not compared; raw committed-state captures '
                                 'are needed for numeric deltas'),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'first_differing_position': result['first_differing_position'],
                      'token_divergence': token_divergence,
                      'positions': [{'position': row['position'], 'different_gdn_count': row['different_gdn_count'],
                                     'first_differing_gdn_ordinal': row['different_gdn_ordinals'][0]
                                     if row['different_gdn_ordinals'] else None}
                                    for row in comparisons]}, indent=2))


if __name__ == '__main__':
    main()
