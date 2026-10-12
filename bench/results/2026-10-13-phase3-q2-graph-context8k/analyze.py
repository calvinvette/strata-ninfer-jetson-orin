#!/usr/bin/env python3
"""Reconcile Q2_0 graph owner events with NVMap and supervisor samples."""
import hashlib
import json
import re
import sys
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def arg_value(args, key):
    return args[args.index(key) + 1]


def analyze_run(path):
    config = json.loads((path / 'server-config.json').read_text())
    result = json.loads((path / 'result.json').read_text())
    supervisor = json.loads((path / 'supervisor/result.json').read_text())
    owners = json.loads((path / 'owner-summary.json').read_text())
    args = config['args']
    spec = int(arg_value(args, '--spec'))
    context = int(arg_value(args, '--max-context'))
    cache = int(arg_value(args, '--expert-cache'))
    log_path = path / 'engine.log'
    log = log_path.read_text(errors='replace')
    events = []
    for line in log.splitlines():
        if 'graph_instantiate' not in line:
            continue
        if 'owner":"verifier"' not in line and 'owner":"verifier-commit-graph"' not in line:
            continue
        match = re.search(r'monotonic_s":([0-9.]+)', line)
        if match:
            owner = line.split('"owner":"', 1)[1].split('"', 1)[0]
            events.append({'monotonic_s': float(match.group(1)), 'owner': owner})
    samples = read_jsonl(path / 'nvmap-clients.jsonl')
    before_event = max((row for row in samples if row['monotonic_s'] < events[0]['monotonic_s']),
                       key=lambda row: row['monotonic_s'])
    after_event = min((row for row in samples if row['monotonic_s'] > events[-1]['monotonic_s']),
                      key=lambda row: row['monotonic_s'])
    process_id = next(row['pid'] for row in before_event['clients'] if row['process'] == 'strata')

    def process_bytes(row):
        return next(client['size_bytes'] for client in row['clients'] if client['pid'] == process_id)

    cgroup_path = next((cg['path'] for row in read_jsonl(path / 'supervisor/memory.jsonl')
                        for cg in row['cgroups'] if f"run-" in cg['path'] and cg.get('max_bytes')),
                       None)
    memory_samples = read_jsonl(path / 'supervisor/memory.jsonl')
    scope_rows = [cg for row in memory_samples for cg in row['cgroups']
                  if cg['path'] == cgroup_path] if cgroup_path else []
    oom = max((cg.get('memory_events', {}).get('oom', 0) for cg in scope_rows), default=None)
    oom_kill = max((cg.get('memory_events', {}).get('oom_kill', 0) for cg in scope_rows), default=None)
    clocks = {'cpu': [], 'gpu': [], 'emc': []}
    for row in memory_samples:
        observations = row.get('clock_observations', {})
        clocks['cpu'].extend(value['hz'] / 1e6 for value in observations.get('cpu', {}).values())
        for device in ('gpu', 'emc'):
            if observations.get(device, {}).get('hz'):
                clocks[device].append(observations[device]['hz'] / 1e6)
    state_rows = re.findall(r'strata serve: STATE_HASH L=.*', log)
    check = result.get('checks', [{}])[0]
    return {
        'spec': spec, 'configured_context': context, 'health_context': result.get('health', {}).get('max_context'),
        'expert_cache_slots': cache, 'request_status': check.get('status'),
        'prompt_tokens': check.get('usage', {}).get('prompt_tokens'),
        'completion_tokens': check.get('usage', {}).get('completion_tokens'),
        'completion_text': check.get('text'),
        'clock_range_mhz': {device: [min(values), max(values)] if values else None
                            for device, values in clocks.items()},
        'state_hash': state_rows[-1] if state_rows else None,
        'graph_events': events,
        'successful_verifier_graphs': sum(event['owner'] == 'verifier' for event in events),
        'successful_commit_graphs': sum(event['owner'] == 'verifier-commit-graph' for event in events),
        'nvmap_bytes_before_first_graph': process_bytes(before_event),
        'nvmap_bytes_after_last_graph': process_bytes(after_event),
        'nvmap_interval_delta_bytes': process_bytes(after_event) - process_bytes(before_event),
        'nvmap_samples': len(samples),
        'owner_allocation_events': owners['allocation_events'],
        'owner_free_events': owners['free_events'],
        'weight_arena_live_bytes': owners['observed_allocation_bytes_by_device']['live_at_log_end'].get('0', 0),
        'minimum_host_available_bytes': supervisor['minimum_available_bytes'],
        'minimum_effective_headroom_bytes': supervisor['minimum_admission_available_bytes'],
        'supervisor_status': supervisor['status'], 'oom_events': oom, 'oom_kill_events': oom_kill,
        'engine_log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest(),
    }


def main():
    root = Path(sys.argv[1]).resolve()
    runs = [root, root / 'repeat-02', root / 'repeat-03']
    rows = [analyze_run(path) for path in runs]
    state_matches = len({row['state_hash'] for row in rows}) == 1
    deltas = [row['nvmap_interval_delta_bytes'] for row in rows]
    common_text = len({row['completion_text'] for row in rows}) == 1
    clocks = {device: [min(row['clock_range_mhz'][device][0] for row in rows),
                       max(row['clock_range_mhz'][device][1] for row in rows)]
              for device in ('cpu', 'gpu', 'emc')}
    output = {
        'scope': 'Q2_0 captured-path NVMap interval at 8K configured context; short API request',
        'model': 'Qwen3.8-Flash-Next-GSQ-RCO Q2_0; model files remained in ~/models/',
        'binary_sha256': hashlib.sha256(Path('build/integration/candidate/strata').read_bytes()).hexdigest(),
        'prompt_tokens': 31, 'generated_tokens': 24, 'configured_context': 8232,
        'expert_cache_slots': 3000, 'speculation_window': 2, 'systemd_memory_max': '28G',
        'same_final_state_all_runs': state_matches,
        'same_completion_text_all_runs': common_text,
        'all_supervisors_passed': all(row['supervisor_status'] == 'pass' for row in rows),
        'all_requests_passed': all(row['request_status'] == 'pass' for row in rows),
        'all_scope_oom_and_oom_kill_counters_zero': all(row['oom_events'] == 0 and row['oom_kill_events'] == 0 for row in rows),
        'all_runs_have_three_verifier_and_one_commit_graph': all(row['successful_verifier_graphs'] == 3 and row['successful_commit_graphs'] == 1 for row in rows),
        'observed_clock_range_mhz': clocks,
        'graph_interval_delta_bytes_by_run': deltas,
        'graph_interval_repeatable': len(set(deltas)) == 1,
        'interpretation_limit': 'NVMap process-owner bracket includes adjacent synchronous allocations; not isolated graph executable cost or total physical RAM.',
        'runs': rows,
    }
    (root / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    if not (output['same_final_state_all_runs'] and output['same_completion_text_all_runs'] and
            output['all_supervisors_passed'] and output['all_requests_passed'] and
            output['all_scope_oom_and_oom_kill_counters_zero'] and
            output['all_runs_have_three_verifier_and_one_commit_graph'] and
            output['graph_interval_repeatable']):
        raise SystemExit('graph/NVMap repeat invariants failed; inspect analysis.json')
    print(json.dumps({key: output[key] for key in ('same_final_state_all_runs',
          'all_supervisors_passed', 'all_requests_passed', 'graph_interval_delta_bytes_by_run')}, indent=2))


if __name__ == '__main__':
    main()
