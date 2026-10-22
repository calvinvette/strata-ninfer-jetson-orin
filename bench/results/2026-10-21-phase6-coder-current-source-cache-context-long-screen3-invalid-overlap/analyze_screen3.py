#!/usr/bin/env python3
"""Audit three-block long-prompt cache x context screen; no inferential claims."""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = json.loads((ROOT / 'workloads.json').read_text())['workloads'][0]['expected_answer']
EXPECTED_PROMPT_TOKENS = 7501
GIB = 1024 ** 3
CACHE = [1500, 3000]
CONTEXT = [8192, 16384]
METRICS = ('client_ttft_s', 'client_total_s', 'prompt_tokens_per_s', 'decode_tokens_per_s')


def median(xs):
    return statistics.median(xs) if xs else None


def main():
    errors, arms, blocks = [], [], []
    minimum_host = float('inf')
    minimum_admission = float('inf')
    max_events = {k: 0 for k in ('low', 'high', 'max', 'oom', 'oom_kill')}
    for block_n in range(1, 4):
        bdir = ROOT / 'per-cell-scopes' / f'block-{block_n:02d}'
        campaign = json.loads((bdir / 'campaign.json').read_text())
        if campaign.get('rounds_per_cell') != 1 or len(campaign.get('cells', [])) != 4:
            errors.append({'block': block_n, 'error': 'campaign design/count mismatch'})
        b_rows = {}
        for cell in campaign['cells']:
            name = cell['name']
            arm = bdir / name
            reqs = json.loads((arm / 'requests.json').read_text())
            cap = json.loads((arm / 'capabilities.json').read_text())
            sup = json.loads((arm / 'supervisor/result.json').read_text())
            measured = [x for x in reqs.get('checks', []) if not x.get('warmup')]
            warmups = [x for x in reqs.get('checks', []) if x.get('warmup')]
            if cell.get('status') != 'pass' or sup.get('status') != 'pass':
                errors.append({'block': block_n, 'cell': name, 'error': 'cell/supervisor failed'})
            if len(measured) != 1 or len(warmups) != 1:
                errors.append({'block': block_n, 'cell': name, 'error': 'expected one measured request and one warmup',
                               'measured': len(measured), 'warmups': len(warmups)})
            if measured:
                row = measured[0]
                response = row.get('response', {})
                content = ''.join(c.get('message', {}).get('content', '')
                                  for c in response.get('choices', []))
                usage = response.get('usage', {})
                timing = response.get('timings', {})
                if row.get('status') != 'pass' or EXPECTED not in content:
                    errors.append({'block': block_n, 'cell': name, 'error': 'exact answer check failed'})
                if usage.get('prompt_tokens') != EXPECTED_PROMPT_TOKENS:
                    errors.append({'block': block_n, 'cell': name, 'error': 'actual prompt token count mismatch',
                                   'usage': usage})
                vals = {
                    'client_ttft_s': row.get('stream_observation', {}).get('first_visible_delta_s'),
                    'client_total_s': row.get('client_elapsed_s'),
                    'prompt_tokens_per_s': timing.get('prompt_per_second'),
                    'decode_tokens_per_s': timing.get('predicted_per_second'),
                    'actual_prompt_tokens': usage.get('prompt_tokens'),
                    'actual_completion_tokens': usage.get('completion_tokens'),
                    'answer': content,
                }
            else:
                vals = {m: None for m in METRICS}
            minimum_host = min(minimum_host, sup.get('minimum_available_bytes', 0) / GIB)
            minimum_admission = min(minimum_admission,
                                    sup.get('minimum_admission_available_bytes', 0) / GIB)
            if sup.get('minimum_available_bytes', 0) < 6 * GIB:
                errors.append({'block': block_n, 'cell': name, 'error': 'six-GiB host floor breached'})
            memfile = arm / 'supervisor' / 'memory.jsonl'
            samples = [json.loads(x) for x in memfile.read_text().splitlines() if x.strip()]
            scope_seen = False
            events = {k: 0 for k in max_events}
            for s in samples:
                if not s.get('cgroup_v2_observed'):
                    errors.append({'block': block_n, 'cell': name, 'error': 'cgroup v2 not observed'})
                for cg in s.get('cgroups', []):
                    if cg.get('max_bytes') == 28 * GIB:
                        scope_seen = True
                    for key, value in cg.get('memory_events', {}).items():
                        if key in events and isinstance(value, int):
                            events[key] = max(events[key], value)
            if not scope_seen:
                errors.append({'block': block_n, 'cell': name, 'error': '28-GiB scope not observed'})
            for key in max_events:
                max_events[key] = max(max_events[key], events[key])
            for key in ('high', 'max', 'oom', 'oom_kill'):
                if events[key]:
                    errors.append({'block': block_n, 'cell': name, 'error': f'cgroup {key} event', 'count': events[key]})
            engine = cap.get('engine', {})
            slots = engine.get('expert_slots')
            alloc_mib = engine.get('expert_cache_mib')
            key = (cell['expert_cache_argument'], cell['context_tokens'])
            b_rows[key] = vals
            arms.append({'block': block_n, 'name': name, 'cache_budget_mib': key[0],
                         'context_tokens': key[1], **vals, 'expert_slots': slots,
                         'expert_cache_mib': alloc_mib,
                         'minimum_host_available_gib': sup.get('minimum_available_bytes', 0) / GIB,
                         'minimum_admission_available_gib': sup.get('minimum_admission_available_bytes', 0) / GIB,
                         'memory_samples': len(samples), 'cgroup_events': events,
                         'supervisor_status': sup.get('status')})
        blocks.append({'block': block_n, 'seed': campaign.get('seed'), 'cells': b_rows})
    contrasts = []
    for metric in METRICS:
        for context in CONTEXT:
            changes = []
            for block in blocks:
                low = block['cells'][(CACHE[0], context)].get(metric)
                high = block['cells'][(CACHE[1], context)].get(metric)
                if low and high:
                    direction = -1 if metric.endswith('_s') else 1
                    changes.append((high / low - 1) * 100 * direction)
            contrasts.append({'factor': 'cache budget', 'metric': metric,
                              'context_tokens': context, 'block_changes_percent': changes,
                              'median_block_change_percent': median(changes)})
        for cache in CACHE:
            changes = []
            for block in blocks:
                low = block['cells'][(cache, CONTEXT[0])].get(metric)
                high = block['cells'][(cache, CONTEXT[1])].get(metric)
                if low and high:
                    direction = -1 if metric.endswith('_s') else 1
                    changes.append((high / low - 1) * 100 * direction)
            contrasts.append({'factor': 'configured context', 'metric': metric,
                              'cache_budget_mib': cache, 'block_changes_percent': changes,
                              'median_block_change_percent': median(changes)})
        interactions = []
        for block in blocks:
            values = block['cells']
            try:
                low_ctx_cache_effect = values[(CACHE[1], CONTEXT[0])][metric] / values[(CACHE[0], CONTEXT[0])][metric]
                high_ctx_cache_effect = values[(CACHE[1], CONTEXT[1])][metric] / values[(CACHE[0], CONTEXT[1])][metric]
                interactions.append((high_ctx_cache_effect / low_ctx_cache_effect - 1) * 100)
            except (TypeError, ZeroDivisionError):
                pass
        contrasts.append({'factor': 'cache x context interaction', 'metric': metric,
                          'block_ratio_of_ratios_change_percent': interactions,
                          'median_block_ratio_of_ratios_change_percent': median(interactions)})
    out = {'schema': 1, 'scope': 'three independent screening blocks; one measured request per fresh service cell; descriptive medians only, no confidence intervals or promotion claim',
           'expected_answer': EXPECTED, 'expected_prompt_tokens': EXPECTED_PROMPT_TOKENS,
           'arms': arms, 'contrasts': contrasts,
           'minimum_host_available_gib': minimum_host,
           'minimum_admission_available_gib': minimum_admission,
           'maximum_cgroup_events': max_events,
           'energy': 'not measured', 'errors': errors,
           'passed': len(arms) == 12 and not errors}
    (ROOT / 'analysis.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'passed': out['passed'], 'minimum_host_available_gib': minimum_host,
                      'minimum_admission_available_gib': minimum_admission,
                      'maximum_cgroup_events': max_events, 'contrasts': contrasts, 'errors': errors}, indent=2))
    if not out['passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
