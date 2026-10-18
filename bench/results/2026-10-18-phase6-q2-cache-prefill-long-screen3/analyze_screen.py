#!/usr/bin/env python3
"""Validate and summarize the randomized long-workload cache × chunk screen."""
import argparse
import json
import gzip
import random
import re
import statistics
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
ROOT=parser.parse_args().root.resolve()

def read_text(path):
    compressed=path.with_suffix(path.suffix+'.gz')
    if compressed.exists():
        with gzip.open(compressed,'rt') as f:
            return f.read()
    return path.read_text()

EXPECTED='EARLY=COPPER-FERN-482, MIDDLE=NORTH-EMBER-619, LATE=SILVER-OTTER-357'
CACHE=(3000,3500); PREFILL=(32,128); BLOCKS=tuple(f'block-{i:02d}' for i in range(1,4))
GIB=1024**3
cells={}; rows=[]; min_host=None; min_admission=None; samples=0
max_events={'low':0,'high':0,'max':0,'oom':0,'oom_kill':0}; gpu_hz=[]; cpu_hz=[]; tj=[]; emc_status=set()
for block in BLOCKS:
    campaign=json.loads((ROOT/block/'campaign.json').read_text())
    assert campaign['clock_sampling'] is True and campaign['independent_block_confirmation'] is True
    assert campaign['rounds_per_service']==1 and len(campaign['cells'])==4
    for cell in campaign['cells']:
        assert cell['status']=='pass', (block,cell.get('name'),cell.get('reason'))
        folder=ROOT/block/cell['name']
        request=json.loads((folder/'requests.json').read_text())
        measured=[r for r in request['checks'] if not r['warmup']]
        assert len(measured)==1 and measured[0]['status']=='pass'
        r=measured[0]; answer=r['response']['choices'][0]['message']['content']
        usage=r['response']['usage']; timing=r['response']['timings']
        assert answer==EXPECTED, (block,cell['name'],answer)
        assert usage['prompt_tokens']==7501 and usage['completion_tokens']==36
        assert timing['prompt_n']==7501 and timing['predicted_n']==36 and timing.get('cache_n',0)==0
        config=json.loads((folder/'config.json').read_text()); args=config['args']
        cache=int(args[args.index('--expert-cache')+1]); prefill=int(args[args.index('--prefill')+1])
        assert cache==cell['expert_cache_argument'] and prefill==cell['prefill_chunk_tokens']
        cap=json.loads((folder/'capabilities.json').read_text())['engine']
        assert cap['expert_slots']==cache and cap['context']==8192 and cap['kv']=='fp16'
        assert cap['mtp_max']==0 and cap['spec']==2 and cap['pool_workers']==8
        assert cap['conversation_cache_mib']==0
        sup=json.loads((folder/'supervisor/result.json').read_text())
        assert sup['status']=='pass' and sup['floor_bytes']==6*GIB
        memory_rows=[json.loads(line) for line in read_text(folder/'supervisor/memory.jsonl').splitlines()]
        assert memory_rows and sup['minimum_admission_available_bytes']>=6*GIB
        start=r['request_start_monotonic_s']; end=r['request_end_monotonic_s']
        active=[s for s in memory_rows if start<=s['monotonic_s']<=end]
        assert active, (block,cell['name'],'no in-request telemetry')
        request_gpu=[s['clock_observations']['gpu']['hz'] for s in active]
        request_cpu=[v['hz'] for s in active for v in s['clock_observations']['cpu'].values() if v.get('hz')]
        for sample in memory_rows:
            samples+=1; min_host=min(min_host or sample['available_bytes'],sample['available_bytes'])
            min_admission=min(min_admission or sample['admission_available_bytes'],sample['admission_available_bytes'])
            obs=sample['clock_observations']; assert obs['gpu']['hz']>0
            gpu_hz.append(obs['gpu']['hz']); cpu_hz.extend(v['hz'] for v in obs['cpu'].values() if v.get('hz'))
            emc_status.add(obs['emc'].get('status','observed'))
            for cg in sample['cgroups']:
                if cg['max_bytes'] is not None: assert cg['max_bytes']==28*GIB
                for name in max_events:
                    value=cg.get('memory_events',{}).get(name,0)
                    max_events[name]=max(max_events[name],value)
                    assert value==0, (block,cell['name'],name,value)
        for line in read_text(folder/'supervisor/tegrastats.txt').splitlines():
            m=re.search(r'\btj@([0-9.]+)C',line)
            if m: tj.append(float(m.group(1)))
        elapsed=timing['prompt_ms']+timing['predicted_ms']; key=(cache,prefill)
        cells.setdefault(key,{})[block]={'request_ms':elapsed,'prompt_tok_s':timing['prompt_per_second'],
            'decode_tok_s':timing['predicted_per_second']}
        rows.append({'block':block,'cell':cell['name'],'cache_slots':cache,'prefill_chunk':prefill,
            'request_ms':elapsed,'prompt_tok_s':timing['prompt_per_second'],'decode_tok_s':timing['predicted_per_second'],
            'actual_expert_slots':cap['expert_slots'],'minimum_available_bytes':sup['minimum_available_bytes'],
            'minimum_admission_available_bytes':sup['minimum_admission_available_bytes'],
            'request_gpu_hz_median':statistics.median(request_gpu),'request_cpu_hz_median':statistics.median(request_cpu),
            'request_clock_samples':len(active)})
assert len(rows)==12 and len(cells)==4 and all(len(cells[k])==3 for k in cells)
assert min_host>=6*GIB and min_admission>=6*GIB

def bootstrap(values,seed):
    rng=random.Random(seed); draws=sorted(statistics.median(rng.choices(values,k=len(values))) for _ in range(100000))
    return [draws[int(.025*len(draws))],draws[int(.975*len(draws))]]
def contrast(label,values,seed,key='percentage'):
    return {'contrast':label,'block_effects_'+key:values,'median_'+key:statistics.median(values),
            'paired_block_bootstrap_95pct_'+key:bootstrap(values,seed)}
contrasts=[]
for cache in CACHE:
    vals=[100*(cells[(cache,128)][b]['request_ms']/cells[(cache,32)][b]['request_ms']-1) for b in BLOCKS]
    contrasts.append(contrast(f'prefill 128 vs 32 at cache {cache}',vals,cache))
for prefill in PREFILL:
    vals=[100*(cells[(3500,prefill)][b]['request_ms']/cells[(3000,prefill)][b]['request_ms']-1) for b in BLOCKS]
    contrasts.append(contrast(f'cache 3500 vs 3000 at prefill {prefill}',vals,prefill+100))
interaction=[(100*(cells[(3500,128)][b]['request_ms']/cells[(3500,32)][b]['request_ms']-1)
              -100*(cells[(3000,128)][b]['request_ms']/cells[(3000,32)][b]['request_ms']-1)) for b in BLOCKS]
contrasts.append(contrast('cache-by-prefill interaction: chunk effect at 3500 minus at 3000',interaction,20261018,'percentage_points'))
summary={'scope':'Three randomized independent blocks; one measured 7,501-token retrieval request per fresh service/cell; separate 512-token warmup; Q2_0 FP16 KV, MTP off, exact cache slots 3000/3500 and prefill chunks 32/128.',
 'blocks':list(BLOCKS),'cells':rows,'contrasts':contrasts,
 'validation':{'cells':12,'measured_requests':12,'all_answers_exact':True,'all_prompt_completion_counts_7501_36':True,
   'all_supervisors_pass':True,'exact_cache_slots_by_budget':True,'memory_samples':samples,
   'minimum_host_available_bytes':min_host,'minimum_admission_available_bytes':min_admission,
   'six_gib_floor_bytes':6*GIB,'maximum_cgroup_events':max_events,
   'gpu_clock_hz_range':[min(gpu_hz),max(gpu_hz)],'cpu_clock_hz_range':[min(cpu_hz),max(cpu_hz)],
   'emc_readback_status':sorted(emc_status),'tj_celsius_range':[min(tj),max(tj)] if tj else None,
   'energy':'not analyzed in this screen; clocks dynamic; no clock controls'}}
(ROOT/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'validation':summary['validation'],'contrasts':contrasts},indent=2))
