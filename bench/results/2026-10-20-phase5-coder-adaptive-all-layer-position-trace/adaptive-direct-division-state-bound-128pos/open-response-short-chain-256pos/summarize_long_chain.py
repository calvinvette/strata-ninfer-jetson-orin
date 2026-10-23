#!/usr/bin/env python3
"""Summarize token, accepted-state, memory, and run identity for this chain pair."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
campaign = json.loads((ROOT / 'campaign.json').read_text())
state = json.loads((ROOT / 'selected-position-analysis.json').read_text())
summary = {
    'scope': 'same-service short-short-short adaptive vs delayed recovery, 256 generated tokens/request',
    'seed': campaign['seed'],
    'binary_sha256': campaign['binary_sha256'],
    'model_repository': campaign['model_repository'],
    'model_revision': campaign['model_revision'],
    'quantization': campaign['quantization'],
    'prompt_workload_cell': campaign['prompt_workload_cell'],
    'prompt_workload_sha256': campaign['prompt_workload_file_sha256'],
    'sequence': campaign['sequence'],
    'generated_tokens_per_request': campaign['generated_tokens'],
    'runs': {},
}
for run in campaign['runs']:
    arm = run['name']
    requests = run['analysis']['requests']
    initial = next(row['ids'] for row in requests if row['name'] == 'short-512')
    recovery = next(row['ids'] for row in requests if row['name'] == 'short-512-recovery')
    mismatch_indices = [i for i, (a, b) in enumerate(zip(initial, recovery)) if a != b]
    samples = [json.loads(line) for line in (ROOT / arm / 'supervisor/memory.jsonl').read_text().splitlines()]
    events = {}
    for sample in samples:
        for cgroup in sample.get('cgroups', []):
            for key, value in cgroup.get('memory_events', {}).items():
                events[key] = max(events.get(key, 0), value)
    analyzed = state['arms'][arm]
    summary['runs'][arm] = {
        'status': run['status'],
        'elapsed_s': run['elapsed_s'],
        'minimum_available_gib': min(x['available_bytes'] for x in samples) / 2**30,
        'minimum_admission_available_gib': run['minimum_admission_available_bytes'] / 2**30,
        'sample_count': len(samples),
        'max_cgroup_memory_events': events,
        'request_tokens': {row['name']: len(row['ids']) for row in requests},
        'short_recovery_token_mismatches': len(mismatch_indices),
        'first_short_recovery_mismatch_index': mismatch_indices[0] if mismatch_indices else None,
        'state_difference_prefix_count': len(analyzed['short_recovery_state_difference_prefixes']),
        'gdn_hash_difference_prefix_count': len(analyzed['short_recovery_gdn_difference_prefixes']),
        'first_gdn_difference_ordinals': analyzed['first_gdn_difference_ordinals'],
    }
summary['measurement_scope'] = {
    'clock_control': 'none; frequencies observed dynamically',
    'energy': 'not measured',
    'emc_frequency': 'unavailable in debugfs due permissions',
}
(ROOT / 'long-chain-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
