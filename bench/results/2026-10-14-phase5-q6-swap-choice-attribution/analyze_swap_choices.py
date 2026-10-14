#!/usr/bin/env python3
"""Summarize swap-choice and state/output evidence from the supervised reproduction."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACE = ROOT / 'trace'
STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
REQUESTS = ('short-512', 'long-2048', 'short-512-recovery')


def batches(path):
    result = []
    for line in path.read_text().splitlines():
        if 'ADAPT choices count=' not in line:
            continue
        match = re.search(r'ADAPT choices count=(\d+)', line)
        choices = re.findall(r' (\d+:\d+>\d+)', line)
        result.append({'count': int(match.group(1)), 'choices': choices})
    return result


def main():
    data = json.loads((TRACE / 'results.json').read_text())
    if [arm['name'] for arm in data['arms']] != ['mtp0', 'mtp4']:
        raise ValueError('expected MTP-off and MTP4 arms')
    choice_batches = {name: batches(TRACE / f'{name}.log') for name in ('mtp0', 'mtp4')}
    if any(len(rows) != 12 or any(row['count'] != len(row['choices']) for row in rows)
           for rows in choice_batches.values()):
        raise ValueError('expected 12 well-formed swap batches per arm')
    if choice_batches['mtp0'] != choice_batches['mtp4']:
        raise ValueError('swap-choice batches differ between MTP settings')
    request_transitions = [set().union(*[
        set(row['choices']) for row in choice_batches['mtp0'][index * 4:index * 4 + 4]])
        for index in range(3)]
    transition_overlap = {
        f'{REQUESTS[i]} vs {REQUESTS[j]}': len(request_transitions[i] & request_transitions[j])
        for i, j in ((0, 1), (0, 2), (1, 2))
    }
    if any(transition_overlap.values()):
        raise ValueError('incoming/victim transition repeated across sequence requests')

    arms = {arm['name']: arm for arm in data['arms']}
    request_checks = []
    for index, name in enumerate(REQUESTS):
        a, b = arms['mtp0']['requests'][index], arms['mtp4']['requests'][index]
        request_checks.append({
            'request': name,
            'prompt_tokens': a['prompt_tokens'],
            'mtp_outputs_equal': a['ids'] == b['ids'],
            'mtp_state_equal': all(a['state'][key] == b['state'][key] for key in STATE_KEYS),
            'swap_batches': 4,
            'planned_swap_choices': sum(row['count'] for row in choice_batches['mtp0'][index * 4:index * 4 + 4]),
            'unique_swap_transitions': len(set().union(*[
                set(row['choices']) for row in choice_batches['mtp0'][index * 4:index * 4 + 4]])),
        })
    divergence = {}
    for name in ('mtp0', 'mtp4'):
        first, recovery = arms[name]['requests'][0], arms[name]['requests'][2]
        divergence[name] = {
            'changed_token_positions': [i for i, (a, b) in enumerate(zip(first['ids'], recovery['ids'])) if a != b],
            'changed_token_count': sum(a != b for a, b in zip(first['ids'], recovery['ids'])),
            'changed_state_fields': [key for key in STATE_KEYS if first['state'][key] != recovery['state'][key]],
        }
    supervisor = json.loads((ROOT / 'supervisor' / 'result.json').read_text())
    output = {
        'interpretation': 'residency-change association; does not prove numeric cause or semantic impact',
        'prompt_token_sha256': data['prompt_token_sha256'],
        'engine_sha256': arms['mtp0']['engine_sha256'],
        'swap_batches_each_arm': len(choice_batches['mtp0']),
        'swap_batch_choice_counts_each_arm': [row['count'] for row in choice_batches['mtp0']],
        'all_swap_choices_identical_across_mtp': True,
        'cross_request_transition_overlap': transition_overlap,
        'requests': request_checks,
        'short_before_vs_after_long': divergence,
        'supervisor': {
            'status': supervisor['status'],
            'reason': supervisor.get('reason'),
            'returncode': supervisor.get('returncode'),
            'minimum_host_gib': supervisor['minimum_available_bytes'] / 2**30,
            'minimum_admission_gib': supervisor['minimum_admission_available_bytes'] / 2**30,
            'cgroup_pressure_oom_events': {
                key: max(sample['cgroups'][0]['memory_events'][key]
                         for sample in (json.loads(line) for line in (ROOT / 'supervisor' / 'memory.jsonl').read_text().splitlines()))
                for key in ('low', 'high', 'max', 'oom', 'oom_kill')
            },
        },
        'strict_output_state_assertion_passed': data['passed'],
    }
    (ROOT / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
