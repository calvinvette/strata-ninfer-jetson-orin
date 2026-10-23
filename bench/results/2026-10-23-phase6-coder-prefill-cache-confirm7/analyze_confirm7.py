#!/usr/bin/env python3
"""Audit a seven-block held-out Coder prefill x cache confirmation with paired bootstrap intervals."""
import json
import statistics
import random
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_DATA = json.loads((ROOT / 'workloads.json').read_text())['workloads'][0]
EXPECTED = EXPECTED_DATA['expected_answer']
EXPECTED_PROMPT = EXPECTED_DATA['prompt_tokens']
GIB = 1024 ** 3
CACHES = [1500, 3000]
CHUNKS = [32, 128]
METRICS = ('client_ttft_s', 'client_total_s', 'prompt_tokens_per_s', 'decode_tokens_per_s')


def median(values):
    return statistics.median(values) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blocks', type=int, choices=range(1, 8), default=7,
                        help='audit completed blocks only; default requires all seven confirmation blocks')
    block_count = parser.parse_args().blocks
    errors, arms, blocks = [], [], []
    min_host = float('inf')
    min_admission = float('inf')
    max_events = {k: 0 for k in ('low', 'high', 'max', 'oom', 'oom_kill')}
    for block_n in range(1, block_count + 1):
        bdir = ROOT / 'per-cell-scopes' / f'block-{block_n:02d}'
        campaign = json.loads((bdir / 'campaign.json').read_text())
        if campaign.get('rounds_per_cell') != 1 or len(campaign.get('cells', [])) != 4:
            errors.append({'block': block_n, 'error': 'campaign design/count mismatch'})
        b_rows = {}
        for cell in campaign['cells']:
            arm = bdir / cell['name']
            reqs = json.loads((arm / 'requests.json').read_text())
            caps = json.loads((arm / 'capabilities.json').read_text())
            sup = json.loads((arm / 'supervisor' / 'result.json').read_text())
            measured = [x for x in reqs.get('checks', []) if not x.get('warmup')]
            warmups = [x for x in reqs.get('checks', []) if x.get('warmup')]
            if cell.get('status') != 'pass' or sup.get('status') != 'pass':
                errors.append({'block': block_n, 'cell': cell['name'], 'error': 'cell/supervisor failed'})
            if len(measured) != 1 or len(warmups) != 1:
                errors.append({'block': block_n, 'cell': cell['name'], 'error': 'expected one measure and one warmup'})
            vals = {m: None for m in METRICS}
            if measured:
                row = measured[0]
                response = row.get('response', {})
                content = ''.join(c.get('message', {}).get('content', '')
                                  for c in response.get('choices', []))
                usage = response.get('usage', {})
                timing = response.get('timings', {})
                if row.get('status') != 'pass' or EXPECTED not in content:
                    errors.append({'block': block_n, 'cell': cell['name'], 'error': 'exact answer failed'})
                if usage.get('prompt_tokens') != EXPECTED_PROMPT:
                    errors.append({'block': block_n, 'cell': cell['name'], 'error': 'prompt token count mismatch',
                                   'actual': usage.get('prompt_tokens')})
                vals = {'client_ttft_s': row.get('stream_observation', {}).get('first_visible_delta_s'),
                        'client_total_s': row.get('client_elapsed_s'),
                        'prompt_tokens_per_s': timing.get('prompt_per_second'),
                        'decode_tokens_per_s': timing.get('predicted_per_second'),
                        'actual_prompt_tokens': usage.get('prompt_tokens'),
                        'actual_completion_tokens': usage.get('completion_tokens'),
                        'answer': content}
            host = sup.get('minimum_available_bytes', 0) / GIB
            admission = sup.get('minimum_admission_available_bytes', 0) / GIB
            min_host = min(min_host, host)
            min_admission = min(min_admission, admission)
            if host < 6:
                errors.append({'block': block_n, 'cell': cell['name'], 'error': 'six-GiB host floor breached'})
            samples = [json.loads(x) for x in (arm / 'supervisor' / 'memory.jsonl').read_text().splitlines() if x.strip()]
            events = {k: 0 for k in max_events}
            scoped = False
            for sample in samples:
                if not sample.get('cgroup_v2_observed'):
                    errors.append({'block': block_n, 'cell': cell['name'], 'error': 'cgroup v2 missing'})
                for cg in sample.get('cgroups', []):
                    scoped |= cg.get('max_bytes') == 28 * GIB
                    for key in events:
                        events[key] = max(events[key], cg.get('memory_events', {}).get(key, 0))
            if not scoped:
                errors.append({'block': block_n, 'cell': cell['name'], 'error': '28-GiB scope missing'})
            for key, value in events.items():
                max_events[key] = max(max_events[key], value)
                if value:
                    errors.append({'block': block_n, 'cell': cell['name'], 'error': f'cgroup {key} event', 'count': value})
            cache, chunk = cell['expert_cache_slots'], cell['prefill_chunk']
            key = (cache, chunk)
            b_rows[key] = vals
            engine = caps.get('engine', {})
            arms.append({'block': block_n, 'cell': cell['name'], 'cache_slots_requested': cache,
                         'prefill_chunk': chunk, **vals, 'expert_slots_realized': engine.get('expert_slots'),
                         'expert_cache_mib_realized': engine.get('expert_cache_mib'),
                         'minimum_host_available_gib': host,
                         'minimum_admission_available_gib': admission,
                         'cgroup_events': events, 'supervisor_status': sup.get('status')})
        blocks.append({'block': block_n, 'seed': campaign.get('seed'), 'cells': b_rows})

    contrasts = []
    for metric in METRICS:
        for cache in CACHES:
            changes = []
            for block in blocks:
                lo = block['cells'][(cache, CHUNKS[0])].get(metric)
                hi = block['cells'][(cache, CHUNKS[1])].get(metric)
                if lo and hi:
                    sign = -1 if metric in ('client_ttft_s', 'client_total_s') else 1
                    changes.append((hi / lo - 1) * 100 * sign)
            contrasts.append({'factor': 'prefill chunk', 'metric': metric, 'cache_slots': cache,
                              'block_changes_percent': changes, 'median_block_change_percent': median(changes)})
        for chunk in CHUNKS:
            changes = []
            for block in blocks:
                lo = block['cells'][(CACHES[0], chunk)].get(metric)
                hi = block['cells'][(CACHES[1], chunk)].get(metric)
                if lo and hi:
                    sign = -1 if metric in ('client_ttft_s', 'client_total_s') else 1
                    changes.append((hi / lo - 1) * 100 * sign)
            contrasts.append({'factor': 'expert cache slots', 'metric': metric, 'prefill_chunk': chunk,
                              'block_changes_percent': changes, 'median_block_change_percent': median(changes)})
        interactions = []
        for block in blocks:
            values = block['cells']
            try:
                cache_small = values[(CACHES[0], CHUNKS[1])][metric] / values[(CACHES[0], CHUNKS[0])][metric]
                cache_large = values[(CACHES[1], CHUNKS[1])][metric] / values[(CACHES[1], CHUNKS[0])][metric]
                interactions.append((cache_large / cache_small - 1) * 100)
            except (TypeError, ZeroDivisionError):
                pass
        contrasts.append({'factor': 'prefill x cache interaction', 'metric': metric,
                          'block_ratio_of_ratios_change_percent': interactions,
                          'median_block_ratio_of_ratios_change_percent': median(interactions)})
    rng = random.Random(2026102327)
    for contrast in contrasts:
        values = contrast.get('block_changes_percent', contrast.get('block_ratio_of_ratios_change_percent', []))
        if len(values) >= 2:
            draws = [median([rng.choice(values) for _ in values]) for _ in range(10000)]
            draws.sort()
            contrast['paired_block_bootstrap_95_percent_interval'] = [draws[249], draws[9749]]
            contrast['bootstrap_resamples'] = 10000
        else:
            contrast['paired_block_bootstrap_95_percent_interval'] = None
    out = {'schema': 1,
           'scope': f'{block_count} completed randomized held-out confirmation block(s); one measured request and one warmup per fresh service cell; paired block medians with bootstrap confidence intervals',
           'expected_answer': EXPECTED, 'expected_prompt_tokens': EXPECTED_PROMPT,
           'arms': arms, 'contrasts': contrasts, 'minimum_host_available_gib': min_host,
           'minimum_admission_available_gib': min_admission, 'maximum_cgroup_events': max_events,
           'energy': 'not measured', 'errors': errors,
           'passed': len(arms) == block_count * 4 and not errors}
    (ROOT / 'analysis.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'passed': out['passed'], 'minimum_host_available_gib': min_host,
                      'minimum_admission_available_gib': min_admission,
                      'maximum_cgroup_events': max_events, 'contrasts': contrasts,
                      'errors': errors}, indent=2))
    if not out['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
