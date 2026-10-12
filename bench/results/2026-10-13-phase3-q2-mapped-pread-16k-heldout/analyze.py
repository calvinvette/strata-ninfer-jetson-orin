#!/usr/bin/env python3
"""Recompute paired effects and telemetry summaries from the retained run."""
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULT = ROOT / 'experiment-7pairs' / 'results.json'
SUPERVISOR = ROOT / 'supervisor' / 'result.json'
SAMPLES = ROOT / 'supervisor' / 'memory.jsonl'


def effect(control, candidate):
    deltas = [(new / old - 1) * 100 for old, new in zip(control, candidate)]
    rng = random.Random(20261013)
    boot = sorted(statistics.median(deltas[rng.randrange(len(deltas))]
                                    for _ in deltas) for _ in range(100_000))
    return {'median_delta_pct': statistics.median(deltas),
            'bootstrap_95pct_interval_pct': [boot[2499], boot[97499]],
            'pair_deltas_pct': deltas}


def main():
    data = json.loads(RESULT.read_text())
    supervisor = json.loads(SUPERVISOR.read_text())
    rows = [json.loads(line) for line in SAMPLES.read_text().splitlines() if line]
    assert data['passed'] and len(data['pair_comparisons']) == 7
    assert len(data['arms']) == 14
    assert all(not pair['failures'] for pair in data['pair_comparisons'])
    arms = {(row['pair'], row['name']): row for row in data['arms']}
    times = {}
    for component in ('request', 'prompt', 'decode'):
        values = {}
        for name in ('mapped', 'pread'):
            values[name] = []
            for pair in range(7):
                usage = arms[pair, name]['usage']
                values[name].append((usage['prompt_ms'] + usage['decode_ms'])
                                    if component == 'request' else usage[component + '_ms'])
        times[component] = {
            'median_ms': {name: statistics.median(vals) for name, vals in values.items()},
            'pread_vs_mapped': effect(values['mapped'], values['pread'])}
    counters = {}
    for field, source, key in (
        ('major_faults', 'process_io_and_fault_deltas', 'major_faults'),
        ('minor_faults', 'process_io_and_fault_deltas', 'minor_faults'),
        ('block_device_read_bytes', 'host_block_device_reads_during_request', 'read_bytes_delta'),
    ):
        diffs = []
        ratios = []
        for pair in range(7):
            left, right = arms[pair, 'mapped'][source][key], arms[pair, 'pread'][source][key]
            diffs.append(right - left)
            ratios.append(right / left if left else None)
        counters[field] = {
            'median_mapped': statistics.median(arms[pair, 'mapped'][source][key] for pair in range(7)),
            'median_pread': statistics.median(arms[pair, 'pread'][source][key] for pair in range(7)),
            'paired_pread_minus_mapped': diffs,
            'paired_ratio_median_delta_pct': statistics.median((x - 1) * 100 for x in ratios if x is not None),
        }
    memory = {
        'floor_bytes': supervisor['floor_bytes'],
        'minimum_host_available_bytes': min(row['available_bytes'] for row in rows),
        'minimum_effective_headroom_bytes': min(row['admission_available_bytes'] for row in rows),
        'oom_kill_max': max((cg.get('memory_events', {}).get('oom_kill', 0)
                             for row in rows for cg in row.get('cgroups', [])), default=0),
        'sample_count': len(rows),
        'elapsed_s': supervisor.get('elapsed_s'),
        'returncode': supervisor.get('returncode'),
        'status': supervisor.get('status'),
    }
    clocks = {'cpu_mhz': [], 'gpu_mhz': [], 'emc_mhz': []}
    for row in rows:
        observed = row.get('clock_observations', {})
        clocks['cpu_mhz'].extend(v['hz'] / 1e6 for v in observed.get('cpu', {}).values()
                                 if isinstance(v, dict) and isinstance(v.get('hz'), (int, float)))
        gpu = observed.get('gpu', {})
        if isinstance(gpu.get('hz'), (int, float)):
            clocks['gpu_mhz'].append(gpu['hz'] / 1e6)
        emc = observed.get('emc', {})
        if isinstance(emc.get('hz'), (int, float)):
            clocks['emc_mhz'].append(emc['hz'] / 1e6)
    clock_summary = {k: {'samples': len(v), 'min': min(v) if v else None,
                         'median': statistics.median(v) if v else None,
                         'max': max(v) if v else None} for k, v in clocks.items()}
    energy = {}
    for name in ('mapped', 'pread'):
        by_rail = {}
        for rail in ('VIN_SYS_5V0', 'VDD_CPU_CV', 'VDD_GPU_SOC'):
            samples = [row['board_telemetry_during_request']['rail_energy_j_estimate'][rail]
                       for row in data['arms'] if row['name'] == name and
                       rail in row.get('board_telemetry_during_request', {}).get('rail_energy_j_estimate', {})]
            by_rail[rail] = {'n': len(samples), 'median_j': statistics.median(samples) if samples else None}
        energy[name] = by_rail
    output = {'experiment_prompt_sha256': data['prompt_sha256'],
              'prompt_variant': data.get('prompt_variant'), 'prompt_tokens': data['prompt_tokens'],
              'pairs': 7, 'times': times, 'counters': counters,
              'memory': memory, 'clocks': clock_summary,
              'board_energy_by_arm': energy,
              'interpretation_limits': [
                  'rail energy is whole-board system activity, not process-attributed; rails are separate and not additive',
                  'disk reads are whole-device counters and include unrelated host activity and kernel readahead',
                  'page-cache state was not flushed; results are warm/shared-cache observations',
                  'clock observations are dynamic and do not control or normalize frequency',
              ]}
    (ROOT / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'request': times['request'], 'prompt': times['prompt'],
                      'decode': times['decode'], 'memory': memory,
                      'counters': counters}, indent=2))


if __name__ == '__main__':
    main()
