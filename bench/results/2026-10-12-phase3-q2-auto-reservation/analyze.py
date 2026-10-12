"""Validate and summarize the randomized automatic-cache context screen."""
import argparse
import json
from pathlib import Path
import statistics

GIB = 1024 ** 3
CACHE_BLOB_BYTES = 1_382_400


def analyze(campaign, campaign_root):
    runs = campaign['runs']
    expected_contexts = campaign['contexts']
    if len(runs) != len(expected_contexts) * campaign['repetitions_per_context']:
        raise ValueError('campaign is incomplete')
    if any(row['status'] != 'pass' or row['minimum_available_bytes'] < campaign['floor_bytes']
           for row in runs):
        raise ValueError('failed or below-floor cell in campaign')
    if len({row['prompt_sha256'] for row in runs}) != 1:
        raise ValueError('formatted prompt identity differs across cells')
    if len({row['engine_sha256'] for row in runs}) != 1:
        raise ValueError('engine binary identity differs across cells')
    if any(row['generated_ids'] != [32] for row in runs):
        raise ValueError('unexpected output token identity')
    oom_by_run = {}
    for row in runs:
        path = campaign_root / row['name'] / 'supervisor/memory.jsonl'
        samples = [json.loads(line) for line in path.read_text().splitlines() if line]
        oom_by_run[row['name']] = max((events.get(key, 0)
            for sample in samples for cgroup in sample.get('cgroups', [])
            for events in [cgroup.get('memory_events', {})]
            for key in ('oom', 'oom_kill', 'oom_group_kill')), default=0)
    if any(oom_by_run.values()):
        raise ValueError(f'cgroup OOM event observed: {oom_by_run}')

    cells = []
    for context in expected_contexts:
        subset = [row for row in runs if row['context_tokens'] == context]
        if len(subset) != campaign['repetitions_per_context']:
            raise ValueError(f'context {context} has the wrong repeat count')
        reservation_sets = [tuple(sorted((x['label'], x['bytes']) for x in row['reservations']))
                            for row in subset]
        if len(set(reservation_sets)) != 1:
            raise ValueError(f'planned holds vary within context {context}')
        prefill_hold = dict(reservation_sets[0])['expert-cache.prefill-workspace']
        if any(row['owners']['prefill'] > prefill_hold for row in subset):
            raise ValueError(f'prefill owner exceeded its hold at context {context}')
        caches = [row['owners']['expert-cache'] for row in subset]
        if any(value % CACHE_BLOB_BYTES for value in caches):
            raise ValueError(f'expert cache allocation is not whole Q2_0 slots at context {context}')
        device_peaks = [int(row['observed_peak_by_device']['0']) for row in subset]
        cells.append({
            'context_tokens': context,
            'repetitions': len(subset),
            'cache_slots': [value // CACHE_BLOB_BYTES for value in caches],
            'median_cache_requested_bytes': int(statistics.median(caches)),
            'median_cache_requested_gib': statistics.median(caches) / GIB,
            'session_requested_bytes': sorted({row['owners']['session'] for row in subset}),
            'prefill_requested_peak_bytes': sorted({row['owners']['prefill'] for row in subset}),
            'prefill_planned_hold_bytes': prefill_hold,
            'median_unique_device_requested_peak_bytes': int(statistics.median(device_peaks)),
            'minimum_host_available_bytes': min(row['minimum_available_bytes'] for row in subset),
            'output_ids': sorted({tuple(row['generated_ids']) for row in subset}),
        })
    first, second = cells
    cache_delta = first['median_cache_requested_bytes'] - second['median_cache_requested_bytes']
    session_delta = second['session_requested_bytes'][0] - first['session_requested_bytes'][0]
    device_delta = (second['median_unique_device_requested_peak_bytes'] -
                    first['median_unique_device_requested_peak_bytes'])
    return {
        'schema': 1,
        'scope': campaign['scope'],
        'seed': campaign['seed'],
        'order': campaign['order'],
        'engine_sha256': runs[0]['engine_sha256'],
        'prompt_sha256': runs[0]['prompt_sha256'],
        'maximum_cgroup_oom_event_counter_by_run': oom_by_run,
        'cells': cells,
        'delta_8k_minus_64k_cache_requested_bytes': cache_delta,
        'delta_64k_minus_8k_session_requested_bytes': session_delta,
        'delta_64k_minus_8k_device_peak_requested_bytes': device_delta,
        'interpretation': 'requested allocation identities only; no physical-backing or speed inference',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.campaign.read_text()), args.campaign.resolve().parent)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
