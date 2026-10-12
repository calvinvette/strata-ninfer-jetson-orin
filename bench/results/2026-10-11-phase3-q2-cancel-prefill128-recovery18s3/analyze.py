#!/usr/bin/env python3
"""Recompute cancellation, recovery, owner cleanup, and resource checks."""
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]/'tools/integration'))
from owner_observations import summarize
rows=[]
for i in range(3):
 run=ROOT/f'run-{i:02d}'
 result=json.loads((run/'result.json').read_text())
 supervisor=json.loads((run/'supervisor/result.json').read_text())
 log=(run/'engine.log').read_text(errors='replace').splitlines()
 prompt=next((x for x in log if 'prompt 2048 tokens =' in x and 'cancelled' in x),None)
 if prompt is None: raise AssertionError(f'missing cancellation record in run {i}')
 match=re.search(r'\+ (\d+) of 2048 read',prompt)
 if not match: raise AssertionError(prompt)
 owners=summarize(log)
 recovery=result['checks'][-1]
 content=recovery.get('response',{}).get('choices',[{}])[0].get('message',{}).get('content','').strip()
 assert [x['status'] for x in result['checks']]==['pass','pass']
 assert content=='Hello Orin!' and result['server_alive_after_recovery']
 assert supervisor['status']=='pass'
 live=[x for x in owners['owners'] if x['live_observed_requested_bytes']]
 assert len(live)==1 and live[0]['owner']=='weight-arena'
 samples=[json.loads(x) for x in (run/'supervisor/memory.jsonl').read_text().splitlines()]
 oom=any(event.get('oom',0) or event.get('oom_kill',0)
         for sample in samples for cg in sample.get('cgroups',[])
         for event in [cg.get('memory_events',{})])
 assert not oom
 clock=[]
 for sample in samples:
  obs=sample.get('clock_observations',{})
  for cpu in obs.get('cpu',{}).values():
   if cpu.get('hz'): clock.append(('cpu',cpu['hz']))
  if obs.get('gpu',{}).get('hz'): clock.append(('gpu',obs['gpu']['hz']))
 rows.append({'run':i,'cancelled_prompt_tokens':int(match.group(1)),
  'cancel_record':prompt,'recovery_text':content,'recovery_elapsed_s':recovery['elapsed_s'],
  'checks_passed':len(result['checks']),'server_alive':True,
  'supervisor_status':supervisor['status'],'minimum_available_bytes':supervisor['minimum_available_bytes'],
  'allocation_events':owners['allocation_events'],'free_events':owners['free_events'],
  'live_observed_owners':live,'oom_events':False,'clock_samples_mhz':clock})
out={'runs':rows,'all_passed':True,'scope':'correctness and cleanup only; no timing inference or energy result'}
(ROOT/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
for row in rows:
 print(row['run'],'cancelled_at',row['cancelled_prompt_tokens'],'recovery',row['recovery_text'],
       'alloc/free',row['allocation_events'],row['free_events'],'min_avail',row['minimum_available_bytes'])
