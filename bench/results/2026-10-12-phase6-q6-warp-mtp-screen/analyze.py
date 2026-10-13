#!/usr/bin/env python3
"""Audit and summarize the randomized Q6_K warp-dequant × MTP screen."""
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / 'run'
SEED = 202610124
BOOTSTRAPS = 200_000


def median(xs):
    return statistics.median(xs)


def percentile(xs, q):
    xs = sorted(xs)
    return xs[round((len(xs) - 1) * q)]


def bootstrap_interval(values, seed):
    rng = random.Random(seed)
    reps = [median([rng.choice(values) for _ in values]) for _ in range(BOOTSTRAPS)]
    return [percentile(reps, .025), percentile(reps, .975)]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def read_cell(block, condition):
    base = RUN / f'block-{block}-{condition}'
    request = json.loads((base / 'requests.json').read_text())
    measured = [row for row in request['checks'] if not row['warmup']]
    warmups = [row for row in request['checks'] if row['warmup']]
    if len(measured) != 1 or len(warmups) != 1:
        raise ValueError(f'{block}/{condition}: expected one warmup and one measured request')
    q, warm = measured[0], warmups[0]
    response = q['response']
    content = response['choices'][0].get('message', {}).get('content', '')
    timing = response['timings']
    caps = json.loads((base / 'capabilities.json').read_text())['engine']
    sup = json.loads((base / 'supervisor/result.json').read_text())
    return {
        'block': block, 'condition': condition, 'status': q['status'],
        'warmup_status': warm['status'], 'prompt_tokens': response['usage']['prompt_tokens'],
        'completion_tokens': response['usage']['completion_tokens'],
        'warmup_prompt_tokens': warm['response']['usage']['prompt_tokens'],
        'warmup_completion_tokens': warm['response']['usage']['completion_tokens'],
        'output_sha256': digest(content), 'output_text': content,
        'prompt_ms': timing['prompt_ms'], 'decode_ms': timing['predicted_ms'],
        'request_ms': timing['prompt_ms'] + timing['predicted_ms'],
        'client_elapsed_ms': q['client_elapsed_s'] * 1000,
        'cache_n': timing.get('cache_n'), 'draft_n': timing.get('draft_n', 0),
        'draft_n_accepted': timing.get('draft_n_accepted', 0),
        'actual_expert_slots': caps['expert_slots'], 'mtp_max': caps['mtp_max'],
        'minimum_available_bytes': sup['minimum_available_bytes'],
        'minimum_admission_available_bytes': sup['minimum_admission_available_bytes'],
        'supervisor_status': sup['status'], 'supervisor_elapsed_s': sup.get('elapsed_s'),
        'engine_sha256': json.loads((RUN / f'block-{block}-{condition}/requests.json').read_text())
            .get('health', {}).get('engine_sha256'),
    }


campaign = json.loads((RUN / 'experiment.json').read_text())
conditions = ('baseline-mtp0', 'warp-mtp0', 'baseline-mtp4', 'warp-mtp4')
rows = [read_cell(block, condition) for block in range(3) for condition in conditions]
by = {(x['block'], x['condition']): x for x in rows}
checks = []
for row in rows:
    checks.append({'cell': f"{row['block']}/{row['condition']}",
                   'request_pass': row['status'] == 'pass',
                   'warmup_pass': row['warmup_status'] == 'pass',
                   'prompt_512': row['prompt_tokens'] == 512,
                   'completion_64': row['completion_tokens'] == 64,
                   'warmup_512_plus_1': row['warmup_prompt_tokens'] == 512 and row['warmup_completion_tokens'] == 1,
                   'cache_fresh': row['cache_n'] == 0,
                   'cache_slots_3903': row['actual_expert_slots'] == 3903,
                   'supervisor_pass': row['supervisor_status'] == 'pass',
                   'six_gib_floor': row['minimum_available_bytes'] >= 6 * 1024**3 and row['minimum_admission_available_bytes'] >= 6 * 1024**3,
                   'mtp4_drafting_active': (not row['condition'].endswith('mtp4') or (row['draft_n'] > 0 and row['draft_n_accepted'] > 0)),
                   'mtp0_drafting_off': (not row['condition'].endswith('mtp0') or (row['draft_n'] == 0 and row['draft_n_accepted'] == 0))})
for block in range(3):
    hashes = {by[(block, c)]['output_sha256'] for c in conditions}
    checks.append({'cell': f'block-{block}-output-parity', 'all_four_outputs_equal': len(hashes) == 1,
                   'hashes': sorted(hashes)})
qualified = all(all(v for k, v in x.items() if k not in ('cell', 'hashes')) for x in checks)

result = {'schema': 1, 'scope': 'randomized three-block screening; Q6_K warp dequant × MTP off/window4',
          'seed': campaign['seed'], 'planned_blocks': campaign['planned_blocks'],
          'checks': checks, 'all_correctness_and_resource_gates_pass': qualified,
          'output_hashes_by_block': {str(b): {c: by[(b,c)]['output_sha256'] for c in conditions} for b in range(3)},
          'cells': {}, 'paired_effects': {}, 'interaction': None,
          'interval_method': f'{BOOTSTRAPS} whole-block bootstrap replicates; screening n=3'}
for condition in conditions:
    items = [by[(b, condition)] for b in range(3)]
    result['cells'][condition] = {'request_ms': [x['request_ms'] for x in items],
                                  'prompt_ms': [x['prompt_ms'] for x in items],
                                  'decode_ms': [x['decode_ms'] for x in items],
                                  'median_request_ms': median([x['request_ms'] for x in items]),
                                  'median_prompt_ms': median([x['prompt_ms'] for x in items]),
                                  'median_decode_ms': median([x['decode_ms'] for x in items]),
                                  'minimum_available_bytes': min(x['minimum_available_bytes'] for x in items),
                                  'minimum_admission_available_bytes': min(x['minimum_admission_available_bytes'] for x in items),
                                  'drafts_offered': [x['draft_n'] for x in items],
                                  'drafts_accepted': [x['draft_n_accepted'] for x in items]}
for mtp in (0, 4):
    metric_rows = {}
    for metric in ('request_ms', 'prompt_ms', 'decode_ms', 'client_elapsed_ms'):
        deltas = []
        for b in range(3):
            baseline = by[(b, f'baseline-mtp{mtp}')][metric]
            candidate = by[(b, f'warp-mtp{mtp}')][metric]
            deltas.append(100 * (candidate / baseline - 1))
        metric_rows[metric] = {'paired_candidate_delta_pct': deltas,
                               'median_paired_delta_pct': median(deltas),
                               'bootstrap_95_pct': bootstrap_interval(deltas, SEED + mtp * 101 + len(metric))}
    result['paired_effects'][f'mtp{mtp}'] = metric_rows
# Interaction contrasts are paired within randomized complete blocks on log latency ratios.
for metric in ('request_ms', 'prompt_ms', 'decode_ms'):
    contrasts = []
    for b in range(3):
        effect4 = math.log(by[(b, 'warp-mtp4')][metric] / by[(b, 'baseline-mtp4')][metric])
        effect0 = math.log(by[(b, 'warp-mtp0')][metric] / by[(b, 'baseline-mtp0')][metric])
        contrasts.append(100 * (math.exp(effect4 - effect0) - 1))
    if metric == 'request_ms':
        result['interaction'] = {'definition': '(warp/baseline at MTP4) / (warp/baseline at MTP0) - 1, calculated within complete block',
                                 'request_candidate_effect_difference_pct': contrasts,
                                 'median_interaction_pct': median(contrasts),
                                 'bootstrap_95_pct': bootstrap_interval(contrasts, SEED + 701)}
    result['interaction'][metric] = {'per_block_pct': contrasts, 'median_pct': median(contrasts),
                                     'bootstrap_95_pct': bootstrap_interval(contrasts, SEED + 702 + len(metric))}
result['raw_cells'] = [{k:v for k,v in row.items() if k != 'output_text'} for row in rows]
result['timing_qualification'] = 'screening deltas are reportable only if all correctness/resource gates pass'
if not qualified:
    result['timing_qualification'] = 'DISQUALIFIED: at least one parity/workload/resource gate failed'
(RUN / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'qualified': qualified, 'paired_effects': result['paired_effects'], 'interaction': result['interaction']}, indent=2))
if not qualified:
    raise SystemExit(1)
