#!/usr/bin/env python3
"""Validate and summarize the completed Q2_0 graph × MTP confirmation."""
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

HERE = Path(__file__).resolve().parent
RUN = HERE / 'run'
CONDITIONS = ('captured-mtp0', 'eager-mtp0', 'captured-mtp2', 'eager-mtp2')
METRICS = ('client_elapsed_s', 'client_ttft_s', 'prompt_tps', 'decode_tps')


def interval(values, seed):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(20000))
    return [samples[int(.025 * len(samples))], samples[int(.975 * len(samples))]]


def ratio_pct(values, seed):
    center = statistics.median(values)
    lo, hi = interval(values, seed)
    return {'paired_ratio_by_block': values,
            'median_change_percent': (center - 1) * 100,
            'paired_bootstrap_95_interval_percent': [(lo - 1) * 100, (hi - 1) * 100]}


def condition_data(block, condition):
    directory = RUN / f'block-{block:02d}-{condition}'
    request_data = json.loads((directory / 'requests.json').read_text())
    measured = [row for row in request_data['checks'] if not row.get('warmup')]
    if len(measured) != 1 or measured[0]['status'] != 'pass':
        raise ValueError(f'{directory.name}: expected one passing measured request')
    row = measured[0]
    usage = row['response']['usage']
    if usage.get('prompt_tokens') != 512 or usage.get('completion_tokens') != 64:
        raise ValueError(f'{directory.name}: API request length mismatch: {usage}')
    counters = row['metrics_after'].get('requests', [])
    raw = next((x for x in counters if x.get('output_tokens') == 64 and x.get('prompt_tokens') == 512), None)
    if raw is None or raw.get('reused') != 0 or raw.get('prompt_read') != 512:
        raise ValueError(f'{directory.name}: fresh prompt counters are missing or inconsistent')
    text = row['response']['choices'][0]['message']['content']
    timing = row['response'].get('timings', {})
    supervisor = json.loads((directory / 'supervisor' / 'result.json').read_text())
    if supervisor['status'] != 'pass' or supervisor['minimum_available_bytes'] < 6 * 1024**3:
        raise ValueError(f'{directory.name}: supervisor/headroom gate failed')
    if supervisor['minimum_admission_available_bytes'] < 3 * 1024**3:
        raise ValueError(f'{directory.name}: workspace admission reserve failed')
    memory = [json.loads(line) for line in (directory / 'supervisor' / 'memory.jsonl').read_text().splitlines()]
    max_events = {}
    for sample in memory:
        for cgroup in sample.get('cgroups', []):
            if cgroup.get('max_bytes') == 28 * 1024**3:
                for key, value in cgroup.get('memory_events', {}).items():
                    max_events[key] = max(max_events.get(key, 0), value)
    return {
        'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'prompt_tokens': usage['prompt_tokens'], 'completion_tokens': usage['completion_tokens'],
        'finish_reason': row['response']['choices'][0].get('finish_reason'),
        'client_elapsed_s': row['client_elapsed_s'],
        'client_ttft_s': row.get('stream_observation', {}).get('first_visible_delta_s'),
        'prompt_tps': timing['prompt_per_second'], 'decode_tps': timing['predicted_per_second'],
        'prompt_ms': timing['prompt_ms'], 'decode_ms': timing['predicted_ms'],
        'drafts_offered': raw['drafts_offered'], 'drafts_accepted': raw['drafts_accepted'],
        'expert_slots': row['metrics_after']['engine'].get('expert_slots'),
        'kv': row['metrics_after']['engine'].get('kv'),
        'minimum_host_gib': supervisor['minimum_available_bytes'] / 1024**3,
        'minimum_admission_gib': supervisor['minimum_admission_available_bytes'] / 1024**3,
        'cgroup_event_maxima': max_events,
    }


def main():
    campaign_path = RUN / 'campaign.json'
    campaign = json.loads(campaign_path.read_text())
    if len(campaign['runs']) != 28 or any(row['status'] != 'pass' for row in campaign['runs']):
        raise ValueError('campaign must have 28 passing cells before analysis')
    blocks = []
    all_hashes = set()
    for block in range(7):
        cells = {condition: condition_data(block, condition) for condition in CONDITIONS}
        workload_and_resource = {(v['prompt_tokens'], v['completion_tokens'], v['expert_slots'], v['kv'])
                                 for v in cells.values()}
        if len(workload_and_resource) != 1:
            raise ValueError(f'block {block}: workload/KV/residency mismatch {workload_and_resource}')
        all_hashes.update(v['text_sha256'] for v in cells.values())
        blocks.append({'block': block,
                       'randomized_order': [r['condition'] for r in campaign['runs'] if r['block'] == block],
                       'conditions': cells,
                       'text_equal_within_block': len({v['text_sha256'] for v in cells.values()}) == 1})

    def get(block, condition, metric):
        return block['conditions'][condition][metric]

    contrasts = {
        'capture_mtp0': ('captured-mtp0', 'eager-mtp0'),
        'capture_mtp2': ('captured-mtp2', 'eager-mtp2'),
        'mtp2_captured': ('captured-mtp2', 'captured-mtp0'),
        'mtp2_eager': ('eager-mtp2', 'eager-mtp0'),
    }
    factors = {}
    seed = campaign['seed']
    for metric_index, metric in enumerate(METRICS):
        for contrast_index, (name, (candidate, baseline)) in enumerate(contrasts.items()):
            ratios = [get(block, candidate, metric) / get(block, baseline, metric) for block in blocks]
            factors[f'{name}_{metric}'] = ratio_pct(ratios, seed + metric_index * 100 + contrast_index)
        ratios = [
            (get(block, 'captured-mtp2', metric) / get(block, 'eager-mtp2', metric)) /
            (get(block, 'captured-mtp0', metric) / get(block, 'eager-mtp0', metric))
            for block in blocks
        ]
        factors[f'capture_x_mtp_{metric}'] = ratio_pct(ratios, seed + metric_index * 100 + 99)

    conditions = {}
    for condition in CONDITIONS:
        conditions[condition] = {}
        for metric in METRICS:
            values = [block['conditions'][condition][metric] for block in blocks]
            conditions[condition][metric] = {'n': len(values), 'median': statistics.median(values),
                                             'maximum_observed': max(values)}
        conditions[condition]['drafts'] = {
            'offered': [b['conditions'][condition]['drafts_offered'] for b in blocks],
            'accepted': [b['conditions'][condition]['drafts_accepted'] for b in blocks],
        }

    all_event_maxima = {}
    for block in blocks:
        for cell in block['conditions'].values():
            for key, value in cell['cgroup_event_maxima'].items():
                all_event_maxima[key] = max(all_event_maxima.get(key, 0), value)
    rows = [cell for block in blocks for cell in block['conditions'].values()]
    report = {
        'scope': '7 independent randomized blocks, one fresh service per condition; held-out exact 512-token prompt and 64-token output; Q2_0, FP16 KV, expert cache 3000, accepted-only cadence 4',
        'n_cells': 28,
        'binary_sha256': campaign['binary_sha256'],
        'prompt_tokens_sha256': json.loads((HERE / 'workloads.json').read_text())['workloads'][0]['tokens_sha256'],
        'prompt_sha256': hashlib.sha256(json.loads((HERE / 'workloads.json').read_text())['workloads'][0]['messages'][0]['content'].encode()).hexdigest(),
        'output_text_unique_sha256_count': len(all_hashes),
        'all_28_outputs_identical': len(all_hashes) == 1,
        'all_blocks_output_equal': all(b['text_equal_within_block'] for b in blocks),
        'all_supervisors_passed': True,
        'minimum_host_availability_gib': min(x['minimum_host_gib'] for x in rows),
        'minimum_admission_availability_gib': min(x['minimum_admission_gib'] for x in rows),
        'maximum_cgroup_event_counters': all_event_maxima,
        'conditions': conditions,
        'paired_factor_effects': factors,
        'uncertainty': '95% percentile bootstrap over seven whole within-block paired ratios; 20,000 resamples; no token-level pseudoreplication',
        'limits': ['one held-out short workload and one Q2_0 artifact', 'dynamic clocks and shared OS file cache',
                   'whole-device energy rails are not process-attributed; energy/token not measured',
                   'the 64-token response cap is not task-quality qualification'],
        'blocks': blocks,
    }
    (HERE / 'analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    campaign['expanded_analysis'] = {'analysis_file': str((HERE / 'analysis.json').resolve()),
                                      'all_28_outputs_identical': report['all_28_outputs_identical'],
                                      'paired_factor_effects': factors,
                                      'minimum_host_availability_gib': report['minimum_host_availability_gib'],
                                      'minimum_admission_availability_gib': report['minimum_admission_availability_gib'],
                                      'maximum_cgroup_event_counters': all_event_maxima}
    campaign_path.write_text(json.dumps(campaign, indent=2) + '\n')
    print(json.dumps({'all_28_outputs_identical': report['all_28_outputs_identical'],
                      'minimum_host_availability_gib': report['minimum_host_availability_gib'],
                      'minimum_admission_availability_gib': report['minimum_admission_availability_gib'],
                      'factors': factors}, indent=2))


if __name__ == '__main__':
    main()
