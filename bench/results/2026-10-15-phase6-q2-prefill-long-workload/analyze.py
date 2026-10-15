#!/usr/bin/env python3
"""Validate and summarize the seven-block held-out Q2_0 prefill run."""
import json
import argparse
import random
import statistics
from pathlib import Path

EXPECTED_CODES = ['COPPER-FERN-482', 'NORTH-EMBER-619', 'SILVER-OTTER-357']
EXPECTED_ANSWER = ('EARLY=COPPER-FERN-482, MIDDLE=NORTH-EMBER-619, '
                   'LATE=SILVER-OTTER-357')


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    fraction = position - low
    return values[low] * (1 - fraction) + values[high] * fraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent,
                        help='directory containing block-01 through block-07')
    args = parser.parse_args()
    root = args.root.resolve()
    records = []
    mins = {'host': None, 'admission': None}
    event_max = {'high': 0, 'max': 0, 'oom': 0, 'oom_kill': 0}
    clock_ranges = {'gpu_clock_hz': [None, None], 'cpu_clock_hz': [None, None]}
    for block_index in range(1, 8):
        block = root / f'block-{block_index:02d}'
        campaign = json.loads((block / 'campaign.json').read_text())
        if len(campaign.get('cells', [])) != 2:
            raise SystemExit(f'{block.name}: expected both prefill cells')
        by_prefill = {}
        for cell in campaign['cells']:
            if cell['status'] != 'pass':
                raise SystemExit(f"{block.name}/{cell['name']}: {cell['status']} {cell.get('reason')}")
            prefill = int(cell['prefill_chunk_tokens'])
            directory = block / cell['name']
            capability = json.loads((directory / 'capabilities.json').read_text())['engine']
            if capability.get('expert_slots_primary') != 3000 or capability.get('mtp_max') != 0:
                raise SystemExit(f'{block.name}/{cell["name"]}: config capability mismatch')
            request_doc = json.loads((directory / 'requests.json').read_text())
            measured = [r for r in request_doc['checks'] if not r.get('warmup')]
            if len(measured) != 1 or measured[0]['status'] != 'pass':
                raise SystemExit(f'{block.name}/{cell["name"]}: expected one passing measured request')
            row = measured[0]
            response = row['response']
            usage = response['usage']
            answer = response['choices'][0]['message']['content']
            if usage.get('prompt_tokens') != 7501 or usage.get('completion_tokens') != 36:
                raise SystemExit(f'{block.name}/{cell["name"]}: prompt/completion count mismatch')
            if answer != EXPECTED_ANSWER or not all(code in answer for code in EXPECTED_CODES):
                raise SystemExit(f'{block.name}/{cell["name"]}: retrieval oracle mismatch: {answer!r}')
            timings = response['timings']
            if timings.get('cache_n') != 0 or timings.get('prompt_n') != 7501:
                raise SystemExit(f'{block.name}/{cell["name"]}: fresh-prefill timing mismatch')
            host_min = None
            admission_min = None
            supervisor = json.loads((directory / 'supervisor' / 'result.json').read_text())
            for key, target in [('minimum_available_bytes', 'host'),
                                ('minimum_admission_available_bytes', 'admission')]:
                value = supervisor.get(key)
                if value is not None:
                    mins[target] = value if mins[target] is None else min(mins[target], value)
                    if target == 'host': host_min = value
                    else: admission_min = value
            telemetry = [json.loads(line) for line in
                         (directory / 'supervisor' / 'memory.jsonl').read_text().splitlines() if line]
            for sample in telemetry:
                available = sample.get('available_bytes')
                admission = sample.get('admission_available_bytes')
                if available is not None:
                    mins['host'] = min(mins['host'], available) if mins['host'] is not None else available
                    host_min = min(host_min, available) if host_min is not None else available
                if admission is not None:
                    mins['admission'] = min(mins['admission'], admission) if mins['admission'] is not None else admission
                    admission_min = min(admission_min, admission) if admission_min is not None else admission
                for group in sample.get('cgroups', []):
                    for key in event_max:
                        event_max[key] = max(event_max[key], group.get('memory_events', {}).get(key, 0))
                observation = sample.get('clock_observations', {})
                values = {'gpu_clock_hz': [observation.get('gpu', {}).get('hz')],
                          'cpu_clock_hz': [cpu.get('hz') for cpu in observation.get('cpu', {}).values()]}
                for key, observations in values.items():
                    for value in observations:
                        if not isinstance(value, (int, float)):
                            continue
                        lo, hi = clock_ranges[key]
                        clock_ranges[key] = [value if lo is None else min(lo, value),
                                             value if hi is None else max(hi, value)]
            by_prefill[prefill] = {'prompt_ms': timings['prompt_ms'],
                                   'request_ms': timings['prompt_ms'] + timings['predicted_ms'],
                                   'prompt_per_second': timings['prompt_per_second'],
                                   'answer': answer, 'host_min_bytes': host_min,
                                   'admission_min_bytes': admission_min}
        records.append({'block': block_index, 'cells': by_prefill})
    request_effects = []
    prefill_rate_effects = []
    for record in records:
        low = record['cells'][32]
        high = record['cells'][128]
        request_effects.append((high['request_ms'] / low['request_ms'] - 1) * 100)
        prefill_rate_effects.append((high['prompt_per_second'] / low['prompt_per_second'] - 1) * 100)
    rng = random.Random(2026101526)
    draws = [statistics.median(rng.choices(request_effects, k=7)) for _ in range(100000)]
    analysis = {
        'scope': 'seven randomized independent blocks; one measured 7,501-token request per fresh service/cell; short separate 512-token warmup',
        'validation': {'blocks': len(records), 'cells': len(records) * 2,
                       'all_cells_pass': True, 'exact_cache_slots': 3000,
                       'all_prompt_tokens_7501': True, 'all_completion_tokens_36': True,
                       'all_retrieval_markers_exact': True,
                       'minimum_host_available_bytes': mins['host'],
                       'minimum_admission_available_bytes': mins['admission'],
                       'six_gib_floor_bytes': 6442450944,
                       'maximum_cgroup_events': event_max,
                       'clock_ranges_hz': clock_ranges},
        'summary': {},
        'paired_effects': {'chunk128_vs32_request_time_percent': request_effects,
                           'median_percent': statistics.median(request_effects),
                           'paired_block_bootstrap_95pct_percent': [percentile(draws, .025), percentile(draws, .975)],
                           'chunk128_vs32_prompt_rate_percent': prefill_rate_effects,
                           'median_prompt_rate_percent': statistics.median(prefill_rate_effects)},
        'blocks': records}
    for prefill in (32, 128):
        requests = [r['cells'][prefill]['request_ms'] for r in records]
        prompt_rates = [r['cells'][prefill]['prompt_per_second'] for r in records]
        analysis['summary'][str(prefill)] = {
            'median_request_ms': statistics.median(requests),
            'median_prompt_tokens_per_second': statistics.median(prompt_rates)}
    (root / 'analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
    print(json.dumps(analysis, indent=2))


if __name__ == '__main__':
    main()
