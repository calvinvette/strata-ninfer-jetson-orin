"""Compare Strata and strict-NInfer generated tokens and persistent state logs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from pool_worker_screen import read_accepted_prefix_trace


STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full',
              'kv', 'mtp', 'stale', 'ple_prev')


def read_final_state(path: Path) -> dict:
    fingerprints = []
    for line in path.read_text(errors='replace').splitlines():
        if line.startswith('strata serve: STATE_HASH L='):
            fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
            missing = set(STATE_KEYS) - fields.keys()
            if missing:
                raise ValueError(f'incomplete final state fingerprint in {path}: {sorted(missing)}')
            fingerprints.append({key: fields[key] for key in STATE_KEYS})
    if not fingerprints:
        raise ValueError(f'no final state fingerprint in {path}')
    return fingerprints[-1]


def read_arm(path: Path) -> dict:
    trace = read_accepted_prefix_trace(path)
    if not trace:
        raise ValueError(f'no accepted-prefix state trace in {path}')
    tokens = [token for row in trace for token in row['token_ids']]
    cumulative = 0
    prefixes = {}
    for row in trace:
        cumulative += row['committed']
        if cumulative in prefixes:
            raise ValueError(f'duplicate accepted-token boundary {cumulative} in {path}')
        prefixes[cumulative] = row['state']
    return {'tokens': tokens, 'prefixes': prefixes, 'final_state': read_final_state(path),
            'trace_entries': len(trace)}


def compare(strata_log: Path, ninfer_log: Path) -> dict:
    strata, ninfer = read_arm(strata_log), read_arm(ninfer_log)
    common = sorted(strata['prefixes'].keys() & ninfer['prefixes'].keys())
    checks = []
    for count in common:
        left, right = strata['prefixes'][count], ninfer['prefixes'][count]
        differing = [key for key in STATE_KEYS if left.get(key) != right.get(key)]
        checks.append({'committed_tokens': count, 'equal': not differing,
                       'differing_fields': differing})
    final_differences = [key for key in STATE_KEYS
                         if strata['final_state'].get(key) != ninfer['final_state'].get(key)]
    result = {
        'strata_generated_tokens': strata['tokens'],
        'ninfer_generated_tokens': ninfer['tokens'],
        'token_ids_equal': strata['tokens'] == ninfer['tokens'],
        'strata_trace_entries': strata['trace_entries'],
        'ninfer_trace_entries': ninfer['trace_entries'],
        'common_prefixes': checks,
        'all_common_prefix_states_equal': bool(checks) and all(row['equal'] for row in checks),
        'final_state_equal': not final_differences,
        'final_state_differing_fields': final_differences,
    }
    result['passed'] = (result['token_ids_equal'] and result['all_common_prefix_states_equal']
                        and result['final_state_equal'])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strata-log', type=Path, required=True)
    parser.add_argument('--ninfer-log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.strata_log, args.ninfer_log)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
