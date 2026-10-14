#!/usr/bin/env python3
"""Validate and summarize the seven-block held-out prefill/cache screen."""
import json, random, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED='EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768'
CACHE=[3000,5000]; PREFILL=[32,128]

def get_arg(args, name):
    i=args.index(name)
    return int(args[i+1])

cells={}; rows=[]; minimum=None; actual_caches={}
for campaign_path in sorted(ROOT.glob('block-*/campaign.json')):
    block=campaign_path.parent.name
    campaign=json.loads(campaign_path.read_text())
    assert len(campaign['cells'])==4
    for cell in campaign['cells']:
        assert cell['status']=='pass' and cell['measured_samples']==3
        folder=campaign_path.parent/cell['name']
        req=json.loads((folder/'requests.json').read_text())
        measured=[r for r in req['checks'] if not r['warmup']]
        assert len(measured)==3 and all(r['status']=='pass' for r in measured)
        for r in measured:
            answer=r['response']['choices'][0]['message']['content']
            use=r['response']['usage']; timing=r['response']['timings']
            assert answer==EXPECTED, (block,cell['name'],answer)
            assert use['prompt_tokens']==512 and use['completion_tokens']==47
            assert timing['prompt_n']==512 and timing['predicted_n']==47
            assert timing.get('cache_n',0)==0
        duration=[r['response']['timings']['prompt_ms']+r['response']['timings']['predicted_ms'] for r in measured]
        prompt_rate=[r['response']['timings']['prompt_per_second'] for r in measured]
        decode_rate=[r['response']['timings']['predicted_per_second'] for r in measured]
        cfg=json.loads((folder/'config.json').read_text())
        args=cfg['args']; cache=get_arg(args,'--expert-cache'); prefill=get_arg(args,'--prefill')
        assert cache==cell['expert_cache_argument'] and prefill==cell['prefill_chunk_tokens']
        cap=json.loads((folder/'capabilities.json').read_text())['engine']
        assert 0 < cap['expert_slots'] <= cache and cap['context']==8192 and cap['kv']=='fp16'
        assert cap['mtp_max']==4 and cap['spec']==2 and cap['pool_workers']==8
        assert cap['conversation_cache_mib']==0
        sup=json.loads((folder/'supervisor/result.json').read_text())
        assert sup['status']=='pass' and sup['floor_bytes']==6*1024**3
        minimum=min(minimum or sup['minimum_available_bytes'],sup['minimum_available_bytes'])
        actual_caches.setdefault(cache,set()).add(cap['expert_slots'])
        key=(cache,prefill); cells.setdefault(key,{})[block]={
            'request_ms':statistics.median(duration),
            'prompt_tok_s':statistics.median(prompt_rate),
            'decode_tok_s':statistics.median(decode_rate)}
        rows.append({'block':block,'cell':cell['name'],'request_ms':duration,
                     'median_request_ms':statistics.median(duration),
                     'prompt_tok_s':prompt_rate,'decode_tok_s':decode_rate,
                     'minimum_available_bytes':sup['minimum_available_bytes'],
                     'expert_cache_mib':cap['expert_cache_mib']})
assert len(rows)==28 and len(cells)==4
blocks=sorted({b for v in cells.values() for b in v})
assert len(blocks)==7 and all(len(cells[k])==7 for k in cells)

def bootstrap(values,seed):
    rng=random.Random(seed)
    draws=sorted(statistics.median(rng.choices(values,k=len(values))) for _ in range(100000))
    return [draws[int(.025*len(draws))],draws[int(.975*len(draws))]]

def effect(label, pairs, seed, unit='percent'):
    vals=[100*(a/b-1) for a,b in pairs]
    return {'contrast':label,'block_effects_percent':vals,
            'median_percent':statistics.median(vals),
            'paired_block_bootstrap_95pct_percent':bootstrap(vals,seed)}
contrasts=[]
# Candidate / baseline: 128-token chunk divided by 32-token chunk.
for cache in CACHE:
    contrasts.append(effect(f'prefill 128 vs 32 at cache {cache}',
       [(cells[(cache,128)][b]['request_ms'],cells[(cache,32)][b]['request_ms']) for b in blocks],cache))
    contrasts.append(effect(f'prefill prompt rate 128 vs 32 at cache {cache}',
       [(cells[(cache,128)][b]['prompt_tok_s'],cells[(cache,32)][b]['prompt_tok_s']) for b in blocks],cache+1))
for prefill in PREFILL:
    contrasts.append(effect(f'cache 5000 vs 3000 at prefill {prefill}',
       [(cells[(5000,prefill)][b]['request_ms'],cells[(3000,prefill)][b]['request_ms']) for b in blocks],prefill+100))
interaction=[100*(cells[(5000,128)][b]['request_ms']/cells[(5000,32)][b]['request_ms']-1)
             -100*(cells[(3000,128)][b]['request_ms']/cells[(3000,32)][b]['request_ms']-1)
             for b in blocks]
contrasts.append({'contrast':'cache-by-prefill interaction: chunk effect at 5000 minus at 3000',
 'block_effect_percentage_points':interaction,'median_percentage_points':statistics.median(interaction),
 'paired_block_bootstrap_95pct_percentage_points':bootstrap(interaction,20261016)})
summary={'scope':'Orin AGX; Q2_0; held-out 512-token retrieval/arithmetic prompt; seven randomized blocks crossing prefill chunk 32/128 and expert-cache arguments 3000/5000; independent service per cell, one warmup and three measured requests.',
 'metric':'Engine-reported prompt_ms + predicted_ms per request; cell statistic is median of three measured requests; effects are paired within block. Negative request-time effect means faster. Prompt rate contrasts are relative changes in tok/s.',
 'blocks':blocks,'cells':rows,'contrasts':contrasts,
 'validation':{'cells':28,'measured_requests':84,'all_answers_exact':True,'all_prompt_completion_counts_512_47':True,
 'all_supervisor_pass':True,'minimum_host_available_bytes':minimum,'host_headroom_floor_bytes':6*1024**3,
 'actual_cache_slots_within_requested_budget':True,'contexts':8192,'kv':'fp16','mtp_max':4,'spec':2,'pool_workers':8,
 'prompt_cache':'disabled','expert_slots_by_budget_argument':{str(k):sorted(v) for k,v in actual_caches.items()}}}
(ROOT/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'validation':summary['validation'],'contrasts':contrasts},indent=2))
