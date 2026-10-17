#!/usr/bin/env python3
"""Validate clock-sampled seven-block fixed-slot cache × prefill confirmation."""
import json
import random
import re
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED='EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768'
CACHE=(3000,3500); PREFILL=(32,128); BLOCKS=tuple(f'block-{i:02d}' for i in range(1,8))
GIB=1024**3
cells={}; rows=[]; min_host=None; min_admission=None; samples=0
max_events={'high':0,'max':0,'oom':0,'oom_kill':0}; gpu_hz=[]; cpu_hz=[]; tj=[]; emc_status=set()
for block in BLOCKS:
    campaign=json.loads((ROOT/block/'campaign.json').read_text())
    assert campaign['clock_sampling'] is True and campaign['independent_block_confirmation'] is True
    assert campaign['rounds_per_service']==1 and len(campaign['cells'])==4
    block_name=block
    for cell in campaign['cells']:
        assert cell['status']=='pass'
        folder=ROOT/block/cell['name']
        request=json.loads((folder/'requests.json').read_text())
        measured=[r for r in request['checks'] if not r['warmup']]
        assert len(measured)==1 and measured[0]['status']=='pass'
        r=measured[0]
        answer=r['response']['choices'][0]['message']['content']
        usage=r['response']['usage']; timing=r['response']['timings']
        assert answer==EXPECTED
        assert usage['prompt_tokens']==512 and usage['completion_tokens']==47
        assert timing['prompt_n']==512 and timing['predicted_n']==47 and timing.get('cache_n',0)==0
        config=json.loads((folder/'config.json').read_text()); args=config['args']
        cache=int(args[args.index('--expert-cache')+1]); prefill=int(args[args.index('--prefill')+1])
        assert cache==cell['expert_cache_argument'] and prefill==cell['prefill_chunk_tokens']
        cap=json.loads((folder/'capabilities.json').read_text())['engine']
        assert cap['expert_slots']==cache and cap['context']==8192 and cap['kv']=='fp16'
        assert cap['mtp_max']==0 and cap['spec']==2 and cap['pool_workers']==8
        assert cap['conversation_cache_mib']==0
        sup=json.loads((folder/'supervisor/result.json').read_text())
        assert sup['status']=='pass' and sup['floor_bytes']==6*GIB
        memory_rows=[json.loads(line) for line in (folder/'supervisor/memory.jsonl').read_text().splitlines()]
        assert memory_rows and sup['minimum_admission_available_bytes']>=6*GIB
        request_start=r['request_start_monotonic_s']; request_end=r['request_end_monotonic_s']
        request_samples=[sample for sample in memory_rows
                         if request_start<=sample['monotonic_s']<=request_end]
        assert request_samples, (block,cell['name'],'no in-request clock samples')
        request_gpu_hz=[sample['clock_observations']['gpu']['hz'] for sample in request_samples]
        request_cpu_hz=[value['hz'] for sample in request_samples
                        for value in sample['clock_observations']['cpu'].values() if value.get('hz')]
        request_gpu_hz_median=statistics.median(request_gpu_hz)
        request_cpu_hz_median=statistics.median(request_cpu_hz)
        for sample in memory_rows:
            samples+=1
            min_host=min(min_host or sample['available_bytes'],sample['available_bytes'])
            min_admission=min(min_admission or sample['admission_available_bytes'],sample['admission_available_bytes'])
            observations=sample['clock_observations']
            assert observations and observations['gpu']['hz']>0
            gpu_hz.append(observations['gpu']['hz'])
            cpu_hz.extend(v['hz'] for v in observations['cpu'].values() if v.get('hz'))
            emc_status.add(observations['emc'].get('status','observed'))
            for cg in sample['cgroups']:
                if cg['max_bytes'] is not None:
                    assert cg['max_bytes']==28*GIB
                events=cg.get('memory_events',{})
                for name in max_events:
                    max_events[name]=max(max_events[name],events.get(name,0))
                    assert events.get(name,0)==0
        for line in (folder/'supervisor/tegrastats.txt').read_text(errors='replace').splitlines():
            match=re.search(r'\btj@([0-9.]+)C',line)
            if match:tj.append(float(match.group(1)))
        elapsed=timing['prompt_ms']+timing['predicted_ms']
        key=(cache,prefill)
        cells.setdefault(key,{})[block_name]={'request_ms':elapsed,
            'prompt_tok_s':timing['prompt_per_second'],'decode_tok_s':timing['predicted_per_second']}
        rows.append({'block':block_name,'cell':cell['name'],'cache_slots':cache,
            'prefill_chunk':prefill,'request_ms':elapsed,'prompt_tok_s':timing['prompt_per_second'],
            'decode_tok_s':timing['predicted_per_second'],'actual_expert_slots':cap['expert_slots'],
            'minimum_available_bytes':sup['minimum_available_bytes'],
            'minimum_admission_available_bytes':sup['minimum_admission_available_bytes'],
            'gpu_hz_min':min(s['clock_observations']['gpu']['hz'] for s in memory_rows),
            'gpu_hz_max':max(s['clock_observations']['gpu']['hz'] for s in memory_rows),
            'request_gpu_hz_median':request_gpu_hz_median,
            'request_cpu_hz_median':request_cpu_hz_median,
            'request_clock_samples':len(request_samples)})
assert len(rows)==28 and len(cells)==4 and all(len(cells[k])==7 for k in cells)
assert min_host>=6*GIB and min_admission>=6*GIB
assert all(sorted({r['cache_slots'] for r in rows if r['cache_slots']==c})==[c] for c in CACHE)

def bootstrap(values,seed):
    rng=random.Random(seed)
    draws=sorted(statistics.median(rng.choices(values,k=len(values))) for _ in range(100000))
    return [draws[int(.025*len(draws))],draws[int(.975*len(draws))]]
def effect(label,pairs,seed):
    values=[100*(a/b-1) for a,b in pairs]
    return {'contrast':label,'block_effects_percent':values,'median_percent':statistics.median(values),
            'paired_block_bootstrap_95pct_percent':bootstrap(values,seed)}
contrasts=[]
for cache in CACHE:
    contrasts.append(effect(f'prefill 128 vs 32 at cache {cache}',
        [(cells[(cache,128)][b]['request_ms'],cells[(cache,32)][b]['request_ms']) for b in BLOCKS],cache))
for prefill in PREFILL:
    contrasts.append(effect(f'cache 3500 vs 3000 at prefill {prefill}',
        [(cells[(3500,prefill)][b]['request_ms'],cells[(3000,prefill)][b]['request_ms']) for b in BLOCKS],prefill+100))
interaction=[100*(cells[(3500,128)][b]['request_ms']/cells[(3500,32)][b]['request_ms']-1)
             -100*(cells[(3000,128)][b]['request_ms']/cells[(3000,32)][b]['request_ms']-1)
             for b in BLOCKS]
contrasts.append({'contrast':'cache-by-prefill interaction: chunk effect at 3500 minus at 3000',
    'block_effect_percentage_points':interaction,'median_percentage_points':statistics.median(interaction),
    'paired_block_bootstrap_95pct_percentage_points':bootstrap(interaction,20261017)})
summary={'scope':'Seven randomized independent blocks; Current-source candidate; seven randomized blocks, one measured 512-token retrieval request per fresh service, separate 512-token warmup; Q2_0, MTP off, exact cache slots 3000/3500, prefill chunks 32/128; CPU/GPU clock sampling enabled.',
 'blocks':list(BLOCKS),'cells':rows,'contrasts':contrasts,
 'validation':{'cells':28,'measured_requests':28,'all_answers_exact':True,
   'all_prompt_completion_counts_512_47':True,'all_supervisors_pass':True,
   'actual_cache_slots_exact_by_budget':True,'expert_slots_by_budget_argument':{'3000':[3000],'3500':[3500]},
   'memory_samples':samples,'minimum_host_available_bytes':min_host,
   'minimum_admission_available_bytes':min_admission,'six_gib_floor_bytes':6*GIB,
   'maximum_cgroup_events':max_events,'gpu_clock_hz_range':[min(gpu_hz),max(gpu_hz)],
   'cpu_clock_hz_range':[min(cpu_hz),max(cpu_hz)],'emc_readback_status':sorted(emc_status),
   'tegrastats_tj_celsius_range':[min(tj),max(tj)] if tj else None,
   'energy':'not request-attributed; clocks dynamic; no clock controls'}}
(ROOT/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'validation':summary['validation'],'contrasts':contrasts},indent=2))
