#!/usr/bin/env python3
"""Recompute held-out prefetch staging effects and memory checks."""
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'results.json').read_text())
SUP = json.loads((ROOT / 'supervisor/result.json').read_text())
ROWS = [json.loads(x) for x in (ROOT / 'supervisor/memory.jsonl').read_text().splitlines() if x]
ARMS = {(x['pair'], x['name']): x for x in DATA['arms']}


def effect(a, b):
    deltas = [(y / x - 1) * 100 for x, y in zip(a, b)]
    rng = random.Random(20261014)
    boot = sorted(statistics.median(rng.choice(deltas) for _ in deltas) for _ in range(100_000))
    return {'median_delta_pct': statistics.median(deltas),
            'bootstrap_95pct_interval_pct': [boot[2499], boot[97499]],
            'pair_deltas_pct': deltas}


def main():
    assert DATA['passed'] and len(DATA['pair_comparisons']) == 7 and len(DATA['arms']) == 14
    assert all(not p['failures'] and p['token_ids_equal'] and p['actual_expert_cache_slots_equal']
               and p['persistent_state_equal'] for p in DATA['pair_comparisons'])
    measures = {}
    for label, getter in (
        ('request', lambda u: u['prompt_ms'] + u['decode_ms']),
        ('prompt', lambda u: u['prompt_ms']), ('decode', lambda u: u['decode_ms'])):
        values = {arm: [getter(ARMS[i, arm]['usage']) for i in range(7)]
                  for arm in ('prefetch-fill', 'prefetch-stage')}
        measures[label] = {
            'median_ms': {arm: statistics.median(v) for arm, v in values.items()},
            'prefetch_stage_vs_fill': effect(values['prefetch-fill'], values['prefetch-stage'])}
    memory = {
        'floor_bytes': SUP['floor_bytes'],
        'minimum_host_available_bytes': min(x['available_bytes'] for x in ROWS),
        'minimum_effective_headroom_bytes': min(x['admission_available_bytes'] for x in ROWS),
        'oom_kill_max': max((cg.get('memory_events', {}).get('oom_kill', 0)
                             for row in ROWS for cg in row.get('cgroups', [])), default=0),
        'samples': len(ROWS), 'elapsed_s': SUP['elapsed_s'], 'returncode': SUP['returncode'],
        'status': SUP['status'],
    }
    counters = {}
    for field in ('major_faults', 'minor_faults'):
        vals = {arm: [ARMS[i, arm]['process_io_and_fault_deltas'][field] for i in range(7)]
                for arm in ('prefetch-fill', 'prefetch-stage')}
        counters[field] = {arm: statistics.median(v) for arm, v in vals.items()}
    energy = {arm: {rail: statistics.median(
        x['board_telemetry_during_request']['rail_energy_j_estimate'][rail]
        for x in DATA['arms'] if x['name'] == arm and rail in
        x['board_telemetry_during_request']['rail_energy_j_estimate'])
        for rail in ('VIN_SYS_5V0', 'VDD_CPU_CV', 'VDD_GPU_SOC')}
        for arm in ('prefetch-fill', 'prefetch-stage')}
    out = {'prompt_sha256': DATA['prompt_sha256'], 'pairs': 7, 'times': measures,
           'median_major_minor_faults': counters, 'memory': memory,
           'board_rail_energy_median_j': energy,
           'limits': ['board energy includes unrelated system activity and is not process-attributed',
                      'physical block-device reads are whole-device and include unrelated reads/readahead',
                      'shared page cache was not flushed; warm-cache observations only',
                      'dynamic clock observations are not controlled or normalized']}
    (ROOT / 'analysis.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
