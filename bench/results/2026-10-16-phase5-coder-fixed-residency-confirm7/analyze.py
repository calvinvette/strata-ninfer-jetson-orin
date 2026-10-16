#!/usr/bin/env python3
"""Compare seven paired no-swap/cap-8 Coder recovery sequences."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = ('gdn', 'ple', 'tail', 'pooled', 'pooled_full', 'kv', 'mtp', 'stale', 'dead', 'ple_prev')
ARMS = ('delayed-control', 'adaptive-cap8')
NAMES = ('short-512', 'long-2048', 'short-512-recovery', 'short-512-continuation-1')


def changed_keys(a, b):
    return [k for k in KEYS if a.get(k) != b.get(k)]


def data_for(run_root, block, arm):
    root = run_root / f'block-{block:02d}-{arm}'
    item = json.loads((root / 'result' / 'analysis.json').read_text())
    requests = item['requests']
    if [r['name'] for r in requests] != list(NAMES):
        raise ValueError(f'{root.name}: request sequence mismatch')
    if [r['prompt_tokens'] for r in requests] != [512, 2048, 512, 512]:
        raise ValueError(f'{root.name}: formatted prompt lengths changed')
    if any(len(r['ids']) != 16 for r in requests):
        raise ValueError(f'{root.name}: a request did not return 16 token IDs')
    if item['binary_sha256'] != 'fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b':
        raise ValueError(f'{root.name}: binary identity mismatch')
    sup = json.loads((root / 'supervisor' / 'result.json').read_text())
    if sup['status'] != 'pass' or sup['minimum_available_bytes'] < 6 * 1024**3 or sup['minimum_admission_available_bytes'] < 3 * 1024**3:
        raise ValueError(f'{root.name}: supervisor or memory reserve gate failed')
    memory = [json.loads(line) for line in (root / 'supervisor' / 'memory.jsonl').read_text().splitlines()]
    events = {}
    for sample in memory:
        for group in sample.get('cgroups', []):
            if group.get('max_bytes') == 28 * 1024**3:
                for key, value in group.get('memory_events', {}).items():
                    events[key] = max(events.get(key, 0), value)
    return {'run': item, 'requests': requests, 'minimum_host_gib': sup['minimum_available_bytes'] / 1024**3,
            'minimum_admission_gib': sup['minimum_admission_available_bytes'] / 1024**3,
            'events': events}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, default=HERE / 'campaign-retry2')
    ap.add_argument('--output', type=Path, default=HERE / 'summary.json')
    args = ap.parse_args()
    run_root = args.run.resolve()
    campaign = json.loads((run_root / 'campaign.json').read_text())
    if campaign.get('status') != 'pass' or len(campaign['runs']) != 14 or any(r.get('status') != 'pass' for r in campaign['runs']):
        raise ValueError('expected all 14 supervised services to pass')
    blocks = []
    all_events = {}
    for block in range(7):
        cells = {arm: data_for(run_root, block, arm) for arm in ARMS}
        by_name = {arm: {r['name']: r for r in cells[arm]['requests']} for arm in ARMS}
        comparisons = {}
        for name in NAMES:
            a, b = by_name['delayed-control'][name], by_name['adaptive-cap8'][name]
            comparisons[name] = {
                'token_positions_different': sum(x != y for x, y in zip(a['ids'], b['ids'])),
                'state_keys_different': changed_keys(a['state'], b['state']),
            }
        within = {}
        for arm in ARMS:
            req = by_name[arm]
            within[arm] = {
                'initial_vs_recovery_token_differences': sum(x != y for x, y in zip(req[NAMES[0]]['ids'], req[NAMES[2]]['ids'])),
                'initial_vs_recovery_state_keys_different': changed_keys(req[NAMES[0]]['state'], req[NAMES[2]]['state']),
                'recovery_vs_continuation_token_differences': sum(x != y for x, y in zip(req[NAMES[2]]['ids'], req[NAMES[3]]['ids'])),
                'recovery_vs_continuation_state_keys_different': changed_keys(req[NAMES[2]]['state'], req[NAMES[3]]['state']),
                'route': cells[arm]['run'].get('route', {}),
                'adaptive_byte_verification_passes': cells[arm]['run'].get('adaptive_byte_verification_passes', 0),
                'adaptive_residency_verification_passes': cells[arm]['run'].get('adaptive_residency_verification_passes', 0),
                'minimum_host_gib': cells[arm]['minimum_host_gib'],
                'minimum_admission_gib': cells[arm]['minimum_admission_gib'],
                'cgroup_event_maxima': cells[arm]['events'],
            }
            for k, v in cells[arm]['events'].items():
                all_events[k] = max(all_events.get(k, 0), v)
        blocks.append({'block': block, 'randomized_order': [r['name'] for r in campaign['runs'] if r['block'] == block],
                       'control_vs_adaptive': comparisons, 'within_arm': within})

    def values(arm, key):
        return [b['within_arm'][arm][key] for b in blocks]

    summary = {
        'scope': 'seven randomized independent pairs; same Coder IQ1_M model and same-service four-request short/long/recovery/continuation sequence; correctness/state only',
        'campaign_status': campaign['status'], 'blocks': 7, 'services': 14,
        'binary_sha256': campaign['binary_sha256'], 'model_repository': campaign['model_repository'],
        'model_revision': campaign['model_revision'], 'model_quantization': campaign['model_quantization'],
        'model_shard_sha256': campaign['model_shard_sha256'], 'model_paths': campaign['model_paths'],
        'paired_token_differences_by_request': {
            name: [b['control_vs_adaptive'][name]['token_positions_different'] for b in blocks] for name in NAMES
        },
        'paired_state_key_difference_counts_by_request': {
            name: [len(b['control_vs_adaptive'][name]['state_keys_different']) for b in blocks] for name in NAMES
        },
        'delayed_control_initial_recovery_token_differences': values('delayed-control', 'initial_vs_recovery_token_differences'),
        'delayed_control_initial_recovery_state_keys': values('delayed-control', 'initial_vs_recovery_state_keys_different'),
        'cap8_initial_recovery_token_differences': values('adaptive-cap8', 'initial_vs_recovery_token_differences'),
        'cap8_initial_recovery_state_keys': values('adaptive-cap8', 'initial_vs_recovery_state_keys_different'),
        'delayed_control_recovery_continuation_token_differences': values('delayed-control', 'recovery_vs_continuation_token_differences'),
        'cap8_recovery_continuation_token_differences': values('adaptive-cap8', 'recovery_vs_continuation_token_differences'),
        'minimum_host_gib': min(v for b in blocks for v in (b['within_arm']['delayed-control']['minimum_host_gib'], b['within_arm']['adaptive-cap8']['minimum_host_gib'])),
        'minimum_admission_gib': min(v for b in blocks for v in (b['within_arm']['delayed-control']['minimum_admission_gib'], b['within_arm']['adaptive-cap8']['minimum_admission_gib'])),
        'maximum_cgroup_event_counters': all_events,
        'all_14_services_passed': True,
        'blocks_detail': blocks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'blocks_detail'}, indent=2))


if __name__ == '__main__':
    main()
