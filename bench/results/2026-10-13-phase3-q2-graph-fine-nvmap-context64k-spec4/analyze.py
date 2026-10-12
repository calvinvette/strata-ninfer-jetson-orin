#!/usr/bin/env python3
"""Align fine NVMap process-owner samples with successful verifier graph events."""
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = (ROOT / 'repeat-01', ROOT / 'repeat-02', ROOT / 'repeat-03')
EVENT_OWNERS = ('verifier', 'verifier-commit-graph')


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def process_bytes(row, pid):
    return next(client['size_bytes'] for client in row['clients'] if client['pid'] == pid)


def analyze_run(path):
    # The first successfully launched run stores the passing supervisor in retry/;
    # supervisor/ retains the earlier syntax failure before any model process ran.
    supervisor_path = ROOT / 'supervisor' / 'result.json'
    supervisor = json.loads(supervisor_path.read_text())
    result = json.loads((path / 'result.json').read_text())
    config = json.loads((path / 'server-config.json').read_text())
    samples = load_jsonl(path / 'nvmap-clients.jsonl')
    engine_log = (path / 'engine.log').read_text(errors='replace').splitlines()
    pid = next(client['pid'] for row in samples for client in row['clients']
               if client['process'] == 'strata')
    intervals_ms = [(right['monotonic_s'] - left['monotonic_s']) * 1000
                    for left, right in zip(samples, samples[1:])]
    events = []
    for line in engine_log:
        if 'graph_instantiate' not in line:
            continue
        data = json.loads(line.split('strata integration: ', 1)[1])
        if data.get('owner') not in EVENT_OWNERS:
            continue
        t = data['monotonic_s']
        before = max((row for row in samples if row['monotonic_s'] < t),
                     key=lambda row: row['monotonic_s'])
        after = min((row for row in samples if row['monotonic_s'] >= t),
                    key=lambda row: row['monotonic_s'])
        wide_before = max((row for row in samples if row['monotonic_s'] <= t - 0.010),
                          key=lambda row: row['monotonic_s'])
        wide_after = min((row for row in samples if row['monotonic_s'] >= t + 0.010),
                         key=lambda row: row['monotonic_s'])
        ordinary_events = []
        for raw in engine_log:
            if 'strata integration: {' not in raw:
                continue
            try:
                owner_event = json.loads(raw.split('strata integration: ', 1)[1])
            except (ValueError, json.JSONDecodeError):
                continue
            if (abs(owner_event.get('monotonic_s', 0) - t) <= 0.010 and
                    owner_event.get('device') == 0 and
                    owner_event.get('kind') in ('alloc', 'free', 'allocate', 'release')):
                ordinary_events.append({
                    'offset_ms': (owner_event['monotonic_s'] - t) * 1000,
                    'owner': owner_event.get('owner'), 'kind': owner_event.get('kind'),
                    'bytes': owner_event.get('requested_bytes'),
                })
        events.append({
            'monotonic_s': t, 'owner': data['owner'],
            'nearest_before_gap_ms': (t - before['monotonic_s']) * 1000,
            'nearest_after_gap_ms': (after['monotonic_s'] - t) * 1000,
            'nearest_sample_delta_bytes': process_bytes(after, pid) - process_bytes(before, pid),
            'twenty_ms_event_centered_delta_bytes': process_bytes(wide_after, pid) - process_bytes(wide_before, pid),
            'instrumented_device0_alloc_free_events_within_twenty_ms': ordinary_events,
        })
    requests = result.get('checks', [])
    memory_rows = load_jsonl(ROOT / 'supervisor' / 'memory.jsonl')
    oom = max((cg.get('memory_events', {}).get('oom', 0)
               for row in memory_rows for cg in row.get('cgroups', [])), default=0)
    oom_kill = max((cg.get('memory_events', {}).get('oom_kill', 0)
                    for row in memory_rows for cg in row.get('cgroups', [])), default=0)
    return {
        'path': str(path.relative_to(ROOT)), 'spec': 2,
        'configured_context': config['args'][config['args'].index('--max-context') + 1],
        'request_status': requests[0].get('status') if requests else None,
        'prompt_tokens': requests[0].get('usage', {}).get('prompt_tokens') if requests else None,
        'generated_tokens': requests[0].get('usage', {}).get('completion_tokens') if requests else None,
        'supervisor_status': supervisor['status'],
        'minimum_host_available_bytes': supervisor['minimum_available_bytes'],
        'minimum_effective_headroom_bytes': supervisor['minimum_admission_available_bytes'],
        'oom_events': oom, 'oom_kill_events': oom_kill,
        'nvmap_sample_count': len(samples),
        'nvmap_interval_ms': {'median': statistics.median(intervals_ms), 'max': max(intervals_ms)},
        'events': events,
        'engine_sha256': hashlib.sha256((path / 'engine.log').read_bytes()).hexdigest(),
    }


def main():
    runs = [analyze_run(path) for path in RUNS]
    verifier_rows = [[event for event in run['events'] if event['owner'] == 'verifier']
                     for run in runs]
    counts = {len(row) for row in verifier_rows}
    assert counts == {2} and all(run['request_status'] == 'pass' and
                                 run['supervisor_status'] == 'pass' and
                                 run['oom_events'] == 0 and run['oom_kill_events'] == 0
                                 for run in runs)
    per_index = []
    for i in (0, 1):
        values = [events[i]['twenty_ms_event_centered_delta_bytes'] for events in verifier_rows]
        per_index.append({'verifier_event_index': i + 1,
                          'per_run_twenty_ms_event_centered_deltas_bytes': values,
                          'median_twenty_ms_delta_bytes': statistics.median(values),
                          'range_twenty_ms_delta_bytes': [min(values), max(values)],
                          'no_instrumented_cuda_alloc_free_in_any_window': all(
                              not events[i]['instrumented_device0_alloc_free_events_within_twenty_ms']
                              for events in verifier_rows)})
    reference_path = (ROOT.parent / '2026-10-13-phase3-q2-graph-fine-nvmap-context64k' / 'analysis.json')
    reference = json.loads(reference_path.read_text())
    context_comparison = []
    current = per_index[1]
    earlier = reference['later_verifier_event_brackets'][0]
    context_comparison.append({
        'verifier_event_index': 2,
        'spec2_median_bytes': earlier['median_twenty_ms_delta_bytes'],
        'spec4_median_bytes': current['median_twenty_ms_delta_bytes'],
        'spec4_range_bytes': current['range_twenty_ms_delta_bytes'],
    })
    out = {
        'scope': 'Q2_0 native serving graph captures; 31-token prompt and 24 generated tokens',
        'model': 'Qwen3.8-Flash-Next-GSQ-RCO Q2_0; files remain in ~/models/',
        'configured_context': 65536, 'expert_cache_slots': 3000, 'cli_spec': 4,
        'systemd_memory_max': '28G', 'nvmap_sample_requested_interval_ms': 2,
        'all_requests_passed': all(run['request_status'] == 'pass' for run in runs),
        'all_supervisors_passed': all(run['supervisor_status'] == 'pass' for run in runs),
        'all_oom_and_oom_kill_counters_zero': all(run['oom_events'] == 0 and run['oom_kill_events'] == 0 for run in runs),
        'verifier_event_brackets': per_index,
        'verifier_context65536_spec2_vs_spec4': context_comparison,
        'verifier_graph_instantiation_count': 2,
        'later_verifier_context_comparison': context_comparison,
        'spec2_context65536_reference': str(reference_path.relative_to(ROOT.parent)),
        'interpretation_limit': '20-ms event-centered NVMap process-owner deltas are repeatable brackets, not isolated graph executable size; driver-private and adjacent uninstrumented allocations remain possible.',
        'runs': runs,
        'harness_note': 'Three fresh service processes; each used the same short supported request, spec4 and 64K context reservation.',
    }
    (ROOT / 'analysis.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'verifier_event_brackets': per_index,
        'verifier_context65536_spec2_vs_spec4': context_comparison,
        'verifier_graph_instantiation_count': 2,
                      'all_requests_passed': out['all_requests_passed'],
                      'all_supervisors_passed': out['all_supervisors_passed']}, indent=2))


if __name__ == '__main__':
    main()
