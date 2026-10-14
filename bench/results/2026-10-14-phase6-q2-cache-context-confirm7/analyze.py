#!/usr/bin/env python3
"""Validate and summarize the seven-block held-out cache/context screen."""
import glob, json, random, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = 'EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768'

cells = {}
min_available = None
checks = []
for campaign_path in sorted(ROOT.glob('block-*/campaign.json')):
    campaign = json.loads(campaign_path.read_text())
    block = campaign_path.parent.name
    assert len(campaign['cells']) == 4
    for cell in campaign['cells']:
        assert cell['status'] == 'pass' and cell['measured_samples'] == 3
        name = cell['name']
        folder = campaign_path.parent / name
        req = json.loads((folder / 'requests.json').read_text())
        measured = [x for x in req['checks'] if not x['warmup']]
        assert len(measured) == 3 and all(x['status'] == 'pass' for x in measured)
        for row in measured:
            answer = row['response']['choices'][0]['message']['content']
            usage = row['response']['usage']
            timing = row['response']['timings']
            assert answer == EXPECTED, (block, name, answer)
            assert usage['prompt_tokens'] == 512 and usage['completion_tokens'] == 47
            assert timing['prompt_n'] == 512 and timing['predicted_n'] == 47
        durations = [x['response']['timings']['prompt_ms'] + x['response']['timings']['predicted_ms'] for x in measured]
        median_ms = statistics.median(durations)
        cap = json.loads((folder / 'capabilities.json').read_text())['engine']
        sup = json.loads((folder / 'supervisor/result.json').read_text())
        assert sup['status'] == 'pass' and sup['floor_bytes'] == 6 * 1024**3
        assert cap['expert_slots'] == cell['expert_cache_argument']
        assert cap['max_context'] == cell['context_tokens']
        assert cap['kv'] == 'fp16' and cap['mtp_max'] == 4 and cap['spec'] == 2
        key = (int(cell['expert_cache_argument']), int(cell['context_tokens']))
        cells.setdefault(key, {})[block] = median_ms
        min_available = min(min_available or sup['minimum_available_bytes'], sup['minimum_available_bytes'])
        checks.append({'block': block, 'cell': name, 'request_ms': durations,
                       'median_request_ms': median_ms,
                       'prompt_tok_s': [x['response']['timings']['prompt_per_second'] for x in measured],
                       'decode_tok_s': [x['response']['timings']['predicted_per_second'] for x in measured],
                       'min_available_bytes': sup['minimum_available_bytes'],
                       'expert_cache_mib': cap['expert_cache_mib']})
assert len(cells) == 4 and len(checks) == 28
blocks = sorted({b for _, per_block in cells.items() for b in per_block})
assert len(blocks) == 7

def bootstrap(values, seed):
    rng = random.Random(seed)
    reps = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(100000))
    return [reps[int(.025 * len(reps))], reps[int(.975 * len(reps))]]

def contrast(label, pairs, seed):
    vals = [100 * (a / b - 1) for a, b in pairs]
    return {'contrast': label, 'block_effect_percent': vals,
            'median_percent': statistics.median(vals),
            'paired_block_bootstrap_95pct_percent': bootstrap(vals, seed)}

contrasts = []
for ctx in (8192, 16384):
    pairs = [(cells[(5000,ctx)][b], cells[(3000,ctx)][b]) for b in blocks]
    contrasts.append(contrast(f'expert cache 5000 vs 3000 at context {ctx}', pairs, ctx))
for cache in (3000, 5000):
    pairs = [(cells[(cache,16384)][b], cells[(cache,8192)][b]) for b in blocks]
    contrasts.append(contrast(f'context 16384 vs 8192 at expert cache {cache}', pairs, cache+100))
interaction = [
    100*(cells[(5000,16384)][b]/cells[(3000,16384)][b]-1)
    - 100*(cells[(5000,8192)][b]/cells[(3000,8192)][b]-1)
    for b in blocks
]
contrasts.append({'contrast':'cache-by-context interaction: cache effect at 16K minus cache effect at 8K',
                  'block_effect_percentage_points': interaction,
                  'median_percentage_points': statistics.median(interaction),
                  'paired_block_bootstrap_95pct_percentage_points': bootstrap(interaction, 20261015)})

summary = {
 'scope':'Orin AGX; Q2_0; held-out 512-token retrieval/arithmetic request; randomized 2x2 cache/context cells in seven blocks; each cell used an independent server process, one warmup and three measured requests.',
 'metric':'Per-request prompt_ms + predicted_ms from the engine response, then median of three requests per cell; paired block contrasts; negative percent means faster. This is engine-reported request work time, not end-to-end wall time.',
 'blocks':blocks,'cells':checks,'contrasts':contrasts,
 'validation':{'cells':len(checks),'measured_requests':sum(len(x['request_ms']) for x in checks),
  'all_answers_exact':True,'all_token_counts_512_prompt_47_completion':True,
  'all_supervisor_pass':True,'minimum_available_host_bytes':min_available,
  'host_headroom_floor_bytes':6*1024**3,'all_cache_slots_match_requested':True,
  'all_contexts_match_requested':True,'kv':'fp16','mtp_max':4,'spec':2,
  'prompt_cache':'disabled (capabilities report conversation_cache budget 0)'}
}
(ROOT/'analysis.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({'validation':summary['validation'],'contrasts':contrasts},indent=2))
