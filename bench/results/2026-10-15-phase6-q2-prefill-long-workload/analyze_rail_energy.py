#!/usr/bin/env python3
"""Integrate separate named rail samples over seven paired Q2_0 requests."""
import csv,json,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/integration'))
from request_telemetry import rails_from_lines,window_energy
from summarize_controls import interval
arms=[]
for block in range(1,8):
 for chunk in (32,128):
  name=f'block-{block:02d}/cache3000-prefill{chunk}'
  run=HERE/name
  req=json.loads((run/'requests.json').read_text())
  measured=[x for x in req['checks'] if not x.get('warmup')]
  if len(measured)!=1 or measured[0]['status']!='pass': raise RuntimeError(f'invalid request {name}')
  x=measured[0]
  memory=[json.loads(line) for line in (run/'supervisor/memory.jsonl').read_text().splitlines()]
  offset=memory[0]['wall_time_s']-memory[0]['monotonic_s']
  samples=rails_from_lines((run/'supervisor/tegrastats.txt').read_text().splitlines())
  e=window_energy(samples,x['request_start_monotonic_s']+offset,x['request_end_monotonic_s']+offset)
  tokens=x['response']['usage']['completion_tokens']
  row={'block':block,'chunk':chunk,'request_seconds':x['request_end_monotonic_s']-x['request_start_monotonic_s'],'output_tokens':tokens,'status':e['status'],'reason':e.get('reason'),'joules_by_named_rail':e.get('joules_by_named_rail',{})}
  row['joules_per_output_token_by_named_rail']={k:v/tokens for k,v in row['joules_by_named_rail'].items()}
  arms.append(row)
paired=[]
for b in range(1,8):
 a=next(x for x in arms if x['block']==b and x['chunk']==32); c=next(x for x in arms if x['block']==b and x['chunk']==128)
 if a['status']!='estimated' or c['status']!='estimated': continue
 for rail in sorted(set(a['joules_by_named_rail'])&set(c['joules_by_named_rail'])):
  paired.append({'block':b,'rail':rail,'chunk32_j':a['joules_by_named_rail'][rail],'chunk128_j':c['joules_by_named_rail'][rail],'chunk32_j_per_token':a['joules_per_output_token_by_named_rail'][rail],'chunk128_j_per_token':c['joules_per_output_token_by_named_rail'][rail],'chunk128_over_32_ratio':c['joules_by_named_rail'][rail]/a['joules_by_named_rail'][rail]})
summary=[]
for rail in sorted({x['rail'] for x in paired}):
 xs=[x for x in paired if x['rail']==rail]; ratios=[x['chunk128_over_32_ratio'] for x in xs]; ci=interval(ratios,20261015)
 summary.append({'rail':rail,'paired_blocks':len(xs),'chunk32_median_j':statistics.median(x['chunk32_j'] for x in xs),'chunk128_median_j':statistics.median(x['chunk128_j'] for x in xs),'chunk32_median_j_per_output_token':statistics.median(x['chunk32_j_per_token'] for x in xs),'chunk128_median_j_per_output_token':statistics.median(x['chunk128_j_per_token'] for x in xs),'chunk128_over_32_median_percent_change':(statistics.median(ratios)-1)*100,'paired_bootstrap_95_interval_percent':[(ci[0]-1)*100,(ci[1]-1)*100]})
out={'scope':'Separate named tegrastats rails integrated over the API request window. Includes board idle/background activity; not process-attributed and rails are not summed.','method':'Piecewise-linear integration of instantaneous mW; one-second wall timestamps; brackets both request ends and rejects gaps >2.5 seconds.','attempts':14,'estimated_windows':sum(x['status']=='estimated' for x in arms),'unsupported_windows':sum(x['status']!='estimated' for x in arms),'paired_request_blocks':len({x['block'] for x in paired}),'planned_blocks':7,'per_arm':arms,'paired':paired,'summary':summary}
(HERE/'rail-energy.json').write_text(json.dumps(out,indent=2)+'\n')
with (HERE/'rail-energy-pairs.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(paired[0]),lineterminator='\n');w.writeheader();w.writerows(paired)
print(json.dumps(summary,indent=2))
