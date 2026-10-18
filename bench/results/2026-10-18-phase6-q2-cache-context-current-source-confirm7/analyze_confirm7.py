#!/usr/bin/env python3
"""Validate and summarize the current-source seven-block Q2 cache/context confirmation."""
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'per-cell-scopes'
EXPECTED = 'EARLY=TUNDRA-ORBIT-593, MIDDLE=COBALT-MAPLE-248, LATE=GRANITE-COMET-761, SUM=1602'
CACHE = (3000, 5000)
CONTEXT = (8192, 16384)

cells = {}
minimum_available = None
minimum_admission_available = None
all_events = {k: 0 for k in ('low', 'high', 'max', 'oom', 'oom_kill')}
rows = []
for campaign_path in sorted(RUN.glob('block-*/campaign.json')):
    campaign = json.loads(campaign_path.read_text())
    block = campaign_path.parent.name
    assert len(campaign['cells']) == 4, block
    assert campaign['rounds_per_cell'] == 3, block
    for cell in campaign['cells']:
        assert cell['status'] == 'pass' and cell['measured_samples'] == 3, (block, cell['name'])
        folder = campaign_path.parent / cell['name']
        req = json.loads((folder / 'requests.json').read_text())
        measured = [x for x in req['checks'] if not x['warmup']]
        assert len(measured) == 3 and all(x['status'] == 'pass' for x in measured)
        durations = []
        for row in measured:
            response = row['response']
            answer = response['choices'][0]['message']['content']
            usage = response['usage']
            timing = response['timings']
            assert answer == EXPECTED, (block, cell['name'], answer)
            assert usage['prompt_tokens'] == 512 and timing['prompt_n'] == 512
            assert 1 <= timing['predicted_n'] <= 48
            durations.append(timing['prompt_ms'] + timing['predicted_ms'])
        cap = json.loads((folder / 'capabilities.json').read_text())['engine']
        sup_path = folder / 'supervisor'
        sup = json.loads((sup_path / 'result.json').read_text())
        assert sup['status'] == 'pass' and sup['floor_bytes'] == 6 * 1024**3
        assert cap['expert_slots'] > 0
        assert cap['max_context'] == int(cell['context_tokens'])
        assert cap['kv'] == 'fp16' and cap['pool_workers'] == 8 and cap['mtp_max'] == 0
        assert cap['conversation_cache_mib'] == 0
        key = (int(cell['expert_cache_argument']), int(cell['context_tokens']))
        cells.setdefault(key, {})[block] = statistics.median(durations)
        minimum_available = min(minimum_available or sup['minimum_available_bytes'],
                                sup['minimum_available_bytes'])
        minimum_admission_available = min(
            minimum_admission_available or sup['minimum_admission_available_bytes'],
            sup['minimum_admission_available_bytes'])
        samples = [json.loads(line) for line in (sup_path / 'memory.jsonl').read_text().splitlines() if line.strip()]
        event_max = {k: max((cg.get('memory_events', {}).get(k, 0)
                             for sample in samples for cg in sample.get('cgroups', [])), default=0)
                     for k in all_events}
        for key_event, value in event_max.items():
            all_events[key_event] = max(all_events[key_event], value)
        rows.append({'block': block, 'cell': cell['name'], 'cache_argument': key[0],
                     'context_tokens': key[1], 'requested_cache_argument': key[0],
                     'actual_expert_slots': cap['expert_slots'],
                     'actual_expert_cache_mib': cap['expert_cache_mib'],
                     'kv': cap['kv'], 'mtp_max': cap.get('mtp_max'),
                     'prompt_ms': [x['response']['timings']['prompt_ms'] for x in measured],
                     'decode_ms': [x['response']['timings']['predicted_ms'] for x in measured],
                     'request_ms': durations,
                     'median_request_ms': statistics.median(durations),
                     'prompt_tok_s': [x['response']['timings']['prompt_per_second'] for x in measured],
                     'decode_tok_s': [x['response']['timings']['predicted_per_second'] for x in measured],
                     'minimum_available_bytes': sup['minimum_available_bytes'],
                     'samples': len(samples), 'cgroup_event_max': event_max})

blocks = sorted({b for by_block in cells.values() for b in by_block})
assert len(blocks) == 7 and len(rows) == 28
rows_by_key = {(r['requested_cache_argument'], r['context_tokens']): {} for r in rows}
for r in rows:
    rows_by_key[(r['requested_cache_argument'], r['context_tokens'])][r['block']] = r['actual_expert_slots']

def bootstrap(values, seed):
    rng = random.Random(seed)
    reps = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(100000))
    return [reps[int(.025 * len(reps))], reps[int(.975 * len(reps))]]

def paired(label, pairs, seed):
    effects = [100 * (a / b - 1) for a, b in pairs]
    return {'contrast': label, 'block_effect_percent': effects,
            'median_percent': statistics.median(effects),
            'paired_block_bootstrap_95pct_percent': bootstrap(effects, seed)}

contrasts = []
for ctx in CONTEXT:
    pairs = [(cells[(5000, ctx)][b], cells[(3000, ctx)][b]) for b in blocks]
    contrasts.append(paired(f'expert cache 5000 vs 3000 at context {ctx}', pairs, ctx))
for cache in CACHE:
    pairs = [(cells[(cache, 16384)][b], cells[(cache, 8192)][b]) for b in blocks]
    contrasts.append(paired(f'context 16384 vs 8192 at expert cache {cache}', pairs, cache + 100))
interaction = [100 * (cells[(5000, 16384)][b] / cells[(3000, 16384)][b] - 1)
               - 100 * (cells[(5000, 8192)][b] / cells[(3000, 8192)][b] - 1)
               for b in blocks]
contrasts.append({'contrast': 'cache-by-context interaction: cache effect at 16K minus cache effect at 8K',
                  'block_effect_percentage_points': interaction,
                  'median_percentage_points': statistics.median(interaction),
                  'paired_block_bootstrap_95pct_percentage_points': bootstrap(interaction, 20261018)})

allocation_contrasts = []
for ctx in CONTEXT:
    slot_delta = [rows_by_key[(5000, ctx)][b] - rows_by_key[(3000, ctx)][b] for b in blocks]
    slot_percent = [100 * (rows_by_key[(5000, ctx)][b] / rows_by_key[(3000, ctx)][b] - 1)
                    for b in blocks]
    allocation_contrasts.append({'contrast': f'actual admitted expert slots: requested 5000 vs 3000 at context {ctx}',
                                 'block_effect_slots': slot_delta,
                                 'median_slots': statistics.median(slot_delta),
                                 'paired_block_bootstrap_95pct_slots': bootstrap(slot_delta, ctx + 500),
                                 'block_effect_percent': slot_percent,
                                 'median_percent': statistics.median(slot_percent),
                                 'paired_block_bootstrap_95pct_percent': bootstrap(slot_percent, ctx + 600)})
allocation_interaction = [
    100 * (rows_by_key[(5000, 16384)][b] / rows_by_key[(3000, 16384)][b] - 1)
    - 100 * (rows_by_key[(5000, 8192)][b] / rows_by_key[(3000, 8192)][b] - 1)
    for b in blocks]
allocation_contrasts.append({'contrast': 'actual slot allocation interaction: relative cache effect at 16K minus 8K',
                             'block_effect_percentage_points': allocation_interaction,
                             'median_percentage_points': statistics.median(allocation_interaction),
                             'paired_block_bootstrap_95pct_percentage_points': bootstrap(allocation_interaction, 20261019)})

summary = {'scope': 'Orin AGX; current-source Q2_0; held-out 512-token retrieval/sum task; randomized 2x2 cache/context cells in seven blocks; fresh service per cell; three measured requests plus warmup.',
           'metric': 'Per-request engine-reported prompt_ms + predicted_ms, median of three requests per cell; paired block contrasts. Negative effects mean less time. Not end-to-end wall time.',
           'blocks': blocks, 'cells': rows, 'contrasts': contrasts, 'actual_cache_allocation_contrasts': allocation_contrasts,
           'validation': {'cells': len(rows), 'measured_requests': sum(len(r['request_ms']) for r in rows),
                          'all_answers_exact': True, 'all_prompt_counts_exact_512': True,
                          'all_supervisors_pass': True, 'minimum_available_host_bytes': minimum_available,
                          'minimum_admission_available_bytes': minimum_admission_available,
                          'host_headroom_floor_bytes': 6 * 1024**3,
                          'requested_cache_arguments': sorted(CACHE),
                          'actual_cache_slots_by_cell': {r['block'] + '/' + r['cell']: r['actual_expert_slots'] for r in rows},
                          'actual_cache_slots_match_request_in_every_cell': all(
                              r['actual_expert_slots'] == r['requested_cache_argument'] for r in rows),
                          'all_contexts_match_requested': True,
                          'all_cgroup_event_counters_zero': all(v == 0 for v in all_events.values()),
                          'cgroup_event_maxima': all_events,
                          'model_source': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF@5348543e0147355ac9cbcb031184a3546350988e',
                          'prompt_cache': 'disabled'}}
(ROOT / 'analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'validation': summary['validation'], 'contrasts': contrasts}, indent=2))
