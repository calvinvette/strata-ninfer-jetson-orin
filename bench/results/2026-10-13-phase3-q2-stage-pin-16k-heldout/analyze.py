#!/usr/bin/env python3
"""Reconcile held-out staging timing, state, supervisor memory, and clocks."""
import json
import statistics
import sys
from pathlib import Path


def percentile(values, p):
    return statistics.quantiles(values, n=100, method='inclusive')[p - 1]


def summarize_arm(arm, samples):
    rows = [row for row in samples
            if arm['started_monotonic_s'] <= row['monotonic_s'] <= arm['finished_monotonic_s']]
    cpu = [item['hz'] / 1e6 for row in rows
           for item in row.get('clock_observations', {}).get('cpu', {}).values()]
    gpu = [row['clock_observations']['gpu']['hz'] / 1e6 for row in rows
           if row.get('clock_observations', {}).get('gpu', {}).get('hz')]
    emc = [row['clock_observations']['emc']['hz'] / 1e6 for row in rows
           if row.get('clock_observations', {}).get('emc', {}).get('hz')]
    return {
        'pair': arm['pair'], 'mode': arm['name'], 'sample_count': len(rows),
        'request_ms_prompt_plus_decode': arm['usage']['prompt_ms'] + arm['usage']['decode_ms'],
        'prompt_ms': arm['usage']['prompt_ms'], 'decode_ms': arm['usage']['decode_ms'],
        'cpu_clock_mhz_range': [min(cpu), max(cpu)] if cpu else None,
        'gpu_clock_mhz_range': [min(gpu), max(gpu)] if gpu else None,
        'emc_clock_mhz_range': [min(emc), max(emc)] if emc else None,
        'minimum_host_available_gib': min((row['available_bytes'] / 2**30 for row in rows), default=None),
        'minimum_effective_cgroup_headroom_gib': min(
            (row['admission_available_bytes'] / 2**30 for row in rows), default=None),
        'maximum_swap_used_gib': max((row['swap_used_bytes'] / 2**30 for row in rows), default=None),
    }


def main(root):
    timing = json.loads((root / 'timing7/results.json').read_text())
    correctness = json.loads((root / 'correctness/results.json').read_text())
    supervisor = json.loads((root / 'supervisor-timing7/result.json').read_text())
    samples = [json.loads(line) for line in (root / 'supervisor-timing7/memory.jsonl').read_text().splitlines()
               if line.strip()]
    by_pair = {}
    for arm in timing['arms']:
        by_pair.setdefault(arm['pair'], {})[arm['name']] = arm
    pair_rows = []
    for pair, arms in sorted(by_pair.items()):
        left, right = arms['pageable'], arms['pinned']
        pair_rows.append({
            'pair': pair, 'randomized_order': next(row['order'] for row in timing['pair_comparisons']
                                                     if row['pair'] == pair),
            'pageable_ids': left['ids'], 'pinned_ids': right['ids'],
            'token_ids_equal': left['ids'] == right['ids'],
            'pageable_request_ms': left['usage']['prompt_ms'] + left['usage']['decode_ms'],
            'pinned_request_ms': right['usage']['prompt_ms'] + right['usage']['decode_ms'],
            'pinned_minus_pageable_delta_pct':
                (right['usage']['prompt_ms'] + right['usage']['decode_ms']) /
                (left['usage']['prompt_ms'] + left['usage']['decode_ms']) * 100.0 - 100.0,
        })
    request_ms = {name: [arm['usage']['prompt_ms'] + arm['usage']['decode_ms']
                         for arm in timing['arms'] if arm['name'] == name]
                  for name in ('pageable', 'pinned')}
    state_pair = correctness['pair_comparisons'][0]
    state_arms = {arm['name']: arm for arm in correctness['arms']}
    memory_events = [cg.get('memory_events', {}) for row in samples for cg in row.get('cgroups', [])
                     if 'run-' in cg.get('path', '') and cg.get('max_bytes')]
    oom = max((event.get('oom', 0) for event in memory_events), default=None)
    oom_kill = max((event.get('oom_kill', 0) for event in memory_events), default=None)
    arm_summaries = [summarize_arm(arm, samples) for arm in timing['arms']]
    output = {
        'scope': 'seven-pair timing-only confirmation on held-out exact 16K prompt; paired to separate traced parity pair',
        'model': 'Qwen3.8-Flash-Next-GSQ-RCO Q2_0 Orin-validation; model files remain under ~/models/',
        'binary_sha256': timing['arms'][0]['engine_sha256'],
        'prompt_variant': timing['prompt_variant'], 'prompt_tokens': timing['prompt_tokens'],
        'prompt_token_ids_sha256': timing['prompt_sha256'], 'generated_tokens': timing['generated_tokens'],
        'context': 16424, 'expert_cache_slots': 3000, 'systemd_memory_max': '28G',
        'timing_only_tracing_disabled': True,
        'timing_supervisor_status': supervisor['status'], 'timing_supervisor_returncode': supervisor['returncode'],
        'minimum_host_available_gib': supervisor['minimum_available_bytes'] / 2**30,
        'minimum_effective_cgroup_headroom_gib': supervisor['minimum_admission_available_bytes'] / 2**30,
        'maximum_swap_used_gib': max(row['swap_used_bytes'] for row in samples) / 2**30,
        'scope_oom_events': oom, 'scope_oom_kill_events': oom_kill,
        'same_day_arm_clock_observations': {
            clock: [min(row[clock + '_clock_mhz_range'][0] for row in arm_summaries),
                    max(row[clock + '_clock_mhz_range'][1] for row in arm_summaries)]
            for clock in ('cpu', 'gpu', 'emc')},
        'arms': arm_summaries,
        'pair_rows': pair_rows,
        'paired_effects': timing['paired_effects'],
        'per_mode_request_median_ms': {name: statistics.median(values) for name, values in request_ms.items()},
        'per_mode_request_p95_inclusive_ms': {name: percentile(values, 95) for name, values in request_ms.items()},
        'correctness_pair': {
            'passed': correctness['passed'] and state_pair['token_ids_equal'] and state_pair['persistent_state_equal'],
            'prompt_token_ids_sha256': correctness['prompt_sha256'],
            'token_ids_equal': state_pair['token_ids_equal'],
            'persistent_state_equal': state_pair['persistent_state_equal'],
            'pageable_state': state_arms['pageable']['state'],
            'pinned_state': state_arms['pinned']['state'],
            'pageable_stage_requested_bytes': state_arms['pageable']['stage_requested_bytes'],
            'pinned_stage_requested_bytes': state_arms['pinned']['stage_requested_bytes'],
            'pageable_allocation_events': state_arms['pageable']['owner_observations']['allocation_events'],
            'pageable_free_events': state_arms['pageable']['owner_observations']['free_events'],
            'pinned_allocation_events': state_arms['pinned']['owner_observations']['allocation_events'],
            'pinned_free_events': state_arms['pinned']['owner_observations']['free_events'],
        },
        'all_timing_pairs_token_ids_match': all(row['token_ids_equal'] for row in pair_rows),
        'energy': 'not measured; raw system rails are not integrated or process-attributed',
        'interpretation': 'screening/confirmation for this workload only; no mode promoted unless paired effect and interval meet the project threshold',
    }
    (root / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({key: output[key] for key in (
        'all_timing_pairs_token_ids_match', 'minimum_host_available_gib',
        'minimum_effective_cgroup_headroom_gib', 'scope_oom_events', 'scope_oom_kill_events',
        'paired_effects', 'per_mode_request_median_ms', 'correctness_pair')}, indent=2))
    if not (output['timing_supervisor_status'] == 'pass' and output['timing_supervisor_returncode'] == 0 and
            output['all_timing_pairs_token_ids_match'] and output['correctness_pair']['passed'] and
            output['scope_oom_events'] == 0 and output['scope_oom_kill_events'] == 0):
        raise SystemExit('held-out staging checks failed; inspect analysis.json')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
