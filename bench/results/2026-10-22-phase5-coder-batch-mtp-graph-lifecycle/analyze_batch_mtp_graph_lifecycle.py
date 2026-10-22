#!/usr/bin/env python3
"""Analyze preserved serial, target-only and batch-MTP graph-lifecycle outputs."""
import json
from pathlib import Path
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
batch = json.loads((OUT / 'run-chat/result.json').read_text())
controls = json.loads((OUT / 'run-target-only-final/control-and-batch-outputs.json').read_text())
names = list(controls['prompts'])


def state_rows(path):
    rows = []
    for line in path.read_text(errors='replace').splitlines():
        match = re.search(r'STATE_HASH L=(\d+).*ple_prev=([0-9,-]+)', line)
        if match:
            rows.append({'L': match.group(1), 'ple_prev': match.group(2)})
    return rows


def terminal_rows(rows, arm):
    result = {}
    for name in names:
        committed = controls['prompts'][name] + arm[name]['tokens'][:-1]
        length, tail = str(len(committed)), ','.join(map(str, committed[-2:]))
        matched = [row for row in rows if row['L'] == length and row['ple_prev'] == tail]
        result[name] = {'expected_L': length, 'expected_ple_prev': tail, 'matches': len(matched)}
    return result


def scoped_memory_events(name):
    samples = [json.loads(line) for line in (OUT / name / 'memory.jsonl').read_text().splitlines()
               if line.strip()]
    result = {'samples': len(samples), 'event_maxima': {}}
    for sample in samples:
        candidates = [cg for cg in sample.get('cgroups', []) if cg.get('path', '').endswith('.scope')]
        if candidates:
            cgroup = max(candidates, key=lambda cg: len(cg.get('path', '')))
            for key, value in cgroup.get('memory_events', {}).items():
                result['event_maxima'][key] = max(result['event_maxima'].get(key, 0), value)
    return result


target_log = OUT / 'run-target-only-final/serial-engine.log'
batch_log = OUT / 'run-chat/batch-mtp-engine.log'
target_states = state_rows(target_log)
batch_states = state_rows(batch_log)
target_outputs = controls['control']
batch_outputs = controls['batch_mtp']
outputs = {}
for name in names:
    left = target_outputs[name]['tokens']
    right = batch_outputs[name]['tokens']
    first = next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), None)
    outputs[name] = {'same': left == right, 'target_only_tokens': len(left),
                     'batch_mtp_tokens': len(right), 'first_mismatch_index': first,
                     'target_only_tail': left[-4:], 'batch_mtp_tail': right[-4:]}

layouts = re.findall(r'captured the batch window over slots ([0-9,]+)', batch_log.read_text(errors='replace'))
counts = Counter(layouts)
supervisor = json.loads((OUT / 'supervisor-chat/result.json').read_text())
target_supervisor = json.loads((OUT / 'supervisor-target-only-final2/result.json').read_text())
single_slot = json.loads((OUT / 'run-single-active-slot/result.json').read_text())
single_slot_supervisor = json.loads((OUT / 'supervisor-single-active-slot/result.json').read_text())
two_slots = json.loads((OUT / 'run-two-active-slots/result.json').read_text())
two_slots_supervisor = json.loads((OUT / 'supervisor-two-active-slots/result.json').read_text())
two_target_slots = json.loads((OUT / 'run-two-active-target-slots/result.json').read_text())
two_target_supervisor = json.loads((OUT / 'supervisor-two-active-target-slots/result.json').read_text())

analysis = {
    'scope': 'one current-source Orin Coder IQ1_M batch-MTP correctness/graph diagnostic; not a performance qualification',
    'profile': {'batch_slots': 8, 'batch_mtp': True, 'adaptive_swaps': False,
                'max_new': 96, 'max_context': 1024, 'expert_cache_mib': 1500,
                'serial_target_only_control_profile': 'inherited source config: max_context=8192, expert_cache=3000 MiB; prompts remain below 70 tokens'},
    'outputs_target_only_vs_batch_mtp': outputs,
    'all_outputs_match_target_only': all(row['same'] for row in outputs.values()),
    'single_active_slot_batch_mtp': {
        'profile': single_slot['profile'],
        'outputs_match_serial_mtp2': single_slot['outputs_match'],
        'first_mismatch_index': single_slot['first_mismatch_index'],
        'minimum_available_gib': single_slot_supervisor['minimum_available_bytes'] / 2**30,
        'minimum_admission_available_gib': single_slot_supervisor['minimum_admission_available_bytes'] / 2**30,
        'scope_memory_events': scoped_memory_events('supervisor-single-active-slot'),
    },
    'two_active_slots_batch_mtp': {
        'profile': two_slots['profile'],
        'per_prompt_match': two_slots['per_prompt_match'],
        'first_mismatch_index': two_slots['first_mismatch_index'],
        'minimum_available_gib': two_slots_supervisor['minimum_available_bytes'] / 2**30,
        'minimum_admission_available_gib': two_slots_supervisor['minimum_admission_available_bytes'] / 2**30,
        'scope_memory_events': scoped_memory_events('supervisor-two-active-slots'),
    },
    'two_active_slots_target_only_batch': {
        'profile': two_target_slots['profile'],
        'per_prompt_match': two_target_slots['per_prompt_match'],
        'first_mismatch_index': two_target_slots['first_mismatch_index'],
        'minimum_available_gib': two_target_supervisor['minimum_available_bytes'] / 2**30,
        'minimum_admission_available_gib': two_target_supervisor['minimum_admission_available_bytes'] / 2**30,
        'scope_memory_events': scoped_memory_events('supervisor-two-active-target-slots'),
    },
    'batch_mtp_vs_target_only_batch': {
        name: {
            'same': two_slots['batch_mtp'][name]['tokens'] == two_target_slots['batch_target_only'][name]['tokens'],
            'first_mismatch_index': next((i for i, (a, b) in enumerate(zip(
                two_slots['batch_mtp'][name]['tokens'], two_target_slots['batch_target_only'][name]['tokens']))
                if a != b), None),
        } for name in two_slots['batch_mtp']
    },
    'terminal_state_matching_target_only': terminal_rows(target_states, target_outputs),
    'terminal_state_matching_batch_mtp': terminal_rows(batch_states, batch_outputs),
    'batch_state_coverage': 'engine log contains solo-to-batch handoff state fingerprints but no terminal fingerprint for each completed batch slot; cannot qualify per-slot persistent-state equality',
    'graph_layouts': {'capture_events': len(layouts), 'unique_layouts': len(counts),
                      'recaptured_layouts': {layout: count for layout, count in counts.items() if count > 1},
                      'pool_limit': 64, 'eviction_and_recapture_observed': len(layouts) > 64 and any(count > 1 for count in counts.values())},
    'memory': {
        'batch_minimum_available_gib': supervisor['minimum_available_bytes'] / 2**30,
        'batch_minimum_admission_available_gib': supervisor['minimum_admission_available_bytes'] / 2**30,
        'target_minimum_available_gib': target_supervisor['minimum_available_bytes'] / 2**30,
        'target_minimum_admission_available_gib': target_supervisor['minimum_admission_available_bytes'] / 2**30,
        'batch_scope_memory_events': scoped_memory_events('supervisor-chat'),
        'target_scope_memory_events': scoped_memory_events('supervisor-target-only-final2'),
    },
    'clock_energy': 'dynamic clocks observed; EMC readback denied; energy not request-attributed',
}
(OUT / 'analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
print(json.dumps({key: analysis[key] for key in ('all_outputs_match_target_only', 'graph_layouts',
                                                   'terminal_state_matching_target_only',
                                                   'terminal_state_matching_batch_mtp')}, indent=2))
