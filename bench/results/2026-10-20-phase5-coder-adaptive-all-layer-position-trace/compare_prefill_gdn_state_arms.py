#!/usr/bin/env python3
"""Compare one captured prefill across the control and adaptive service arms."""
import argparse
import json
import re
from pathlib import Path

from compare_prefill_gdn_state_pair import read_prefill, summarize

TRACE = re.compile(r'GDN_STATE_TRACE layer=(\d+) prompt=(\d+) boundary=(\d+) hash=([0-9a-f]{16})')


def read_trace(path, layer):
    records = []
    for line in path.read_text(errors='replace').splitlines():
        match = TRACE.search(line)
        if match and int(match.group(1)) == layer:
            records.append({'prompt_tokens': int(match.group(2)), 'boundary': int(match.group(3)),
                            'hash': match.group(4)})
    prompts = {row['prompt_tokens'] for row in records}
    if len(prompts) != 1 or not records:
        raise ValueError(f'{path}: expected one nonempty prompt trace, found lengths {sorted(prompts)}')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-log', type=Path, required=True)
    parser.add_argument('--control-state', type=Path, required=True)
    parser.add_argument('--adaptive-log', type=Path, required=True)
    parser.add_argument('--adaptive-state', type=Path, required=True)
    parser.add_argument('--layer', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    control_trace = read_trace(args.control_log, args.layer)
    adaptive_trace = read_trace(args.adaptive_log, args.layer)
    prompt_tokens = control_trace[0]['prompt_tokens']
    if adaptive_trace[0]['prompt_tokens'] != prompt_tokens:
        raise ValueError('control and adaptive prompt lengths differ')
    boundaries = [row['boundary'] for row in control_trace]
    if [row['boundary'] for row in adaptive_trace] != boundaries:
        raise ValueError('control and adaptive chunk boundaries differ')

    _, control_snapshots = read_prefill(args.control_state, args.layer)
    _, adaptive_snapshots = read_prefill(args.adaptive_state, args.layer)
    control_snapshots = [r for r in control_snapshots if r['prompt_tokens'] == prompt_tokens]
    adaptive_snapshots = [r for r in adaptive_snapshots if r['prompt_tokens'] == prompt_tokens]
    if len(control_snapshots) != 1 or len(adaptive_snapshots) != 1:
        raise ValueError('expected exactly one end-of-prompt raw state snapshot per service arm')
    if control_snapshots[0]['boundary'] != boundaries[-1] or adaptive_snapshots[0]['boundary'] != boundaries[-1]:
        raise ValueError('raw state snapshot boundary does not match final trace boundary')
    if control_snapshots[0]['recurrent'] != adaptive_snapshots[0]['recurrent']:
        raise ValueError('raw state recurrent dimensions differ')

    chunks = [{'boundary': a['boundary'], 'control_hash': a['hash'], 'adaptive_hash': b['hash'],
               'equal': a['hash'] == b['hash']}
              for a, b in zip(control_trace, adaptive_trace)]
    control_state, adaptive_state = control_snapshots[0], adaptive_snapshots[0]
    result = {
        'layer': args.layer,
        'prompt_tokens': prompt_tokens,
        'chunk_boundaries': boundaries,
        'first_differing_boundary': next((r['boundary'] for r in chunks if not r['equal']), None),
        'chunk_hashes_equal_at_all_boundaries': all(r['equal'] for r in chunks),
        'chunk_comparisons': chunks,
        'control_end_state_sha256': control_state['state_sha256'],
        'adaptive_end_state_sha256': adaptive_state['state_sha256'],
        'end_state_comparison': summarize(control_state['state'], adaptive_state['state'], control_state['recurrent']),
        'interpretation_limit': 'cross-arm prefill differences identify the first differing captured boundary, not the operation that caused it',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('layer', 'prompt_tokens', 'first_differing_boundary',
                                              'chunk_hashes_equal_at_all_boundaries', 'end_state_comparison')}, indent=2))


if __name__ == '__main__':
    main()
