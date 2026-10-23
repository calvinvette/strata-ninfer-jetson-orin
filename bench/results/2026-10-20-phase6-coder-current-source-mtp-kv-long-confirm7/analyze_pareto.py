#!/usr/bin/env python3
"""Summarize the four matched MTP cells on latency/rail-energy coordinates."""
import csv, html, json, statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
campaign=json.loads((HERE/'campaign/campaign.json').read_text())
energy=json.loads((HERE/'rail-energy.json').read_text())
energy_by_run={x['run']:x for x in energy['request_estimates'] if x['request_status']=='estimated'}
summary=[]
for kv in ('fp16','int8'):
 for workload in sorted({r['workload'] for r in campaign['runs']}):
  for window in (0,4):
   arms=[r for r in campaign['runs'] if r['status']=='pass' and r['kv']==kv and r['workload']==workload and r['window']==window]
   if len(arms)!=7: raise RuntimeError(f'expected seven passing blocks, got {len(arms)} for {kv}/{workload}/mtp{window}')
   rail=[]
   for arm in arms:
    e=energy_by_run[arm['name']]['joules_per_output_token_by_named_rail'].get('VIN_SYS_5V0')
    if e is None: raise RuntimeError(f'missing VIN_SYS_5V0 for {arm["name"]}')
    rail.append(e)
   summary.append({'kv':kv,'workload':workload,'mtp_window':window,'paired_blocks':7,
    'median_client_total_s':statistics.median(r['metrics']['client_total_s'] for r in arms),
    'median_client_ttft_s':statistics.median(r['metrics']['client_ttft_s'] for r in arms),
    'median_prompt_tps':statistics.median(r['metrics']['prompt_tps'] for r in arms),
    'median_decode_tps':statistics.median(r['metrics']['decode_tps'] for r in arms),
    'median_vin_sys_5v0_j_per_45_output_tokens':statistics.median(rail),
    'median_min_host_available_gib':statistics.median(r['minimum_available_bytes'] for r in arms)/1024**3,
    'median_min_admission_available_gib':statistics.median(r['minimum_admission_available_bytes'] for r in arms)/1024**3,
    'minimum_admission_available_gib':min(r['minimum_admission_available_bytes'] for r in arms)/1024**3,
    'quality':'all seven arms exact-answer pass'})
# State domination only within identical KV/workload cells; lower latency and lower named-rail energy are both preferred.
for row in summary:
 peers=[x for x in summary if x['kv']==row['kv'] and x['workload']==row['workload']]
 row['dominated_within_cell']=any(x['mtp_window']!=row['mtp_window'] and
  x['median_client_total_s']<=row['median_client_total_s'] and
  x['median_vin_sys_5v0_j_per_45_output_tokens']<=row['median_vin_sys_5v0_j_per_45_output_tokens'] and
  (x['median_client_total_s']<row['median_client_total_s'] or x['median_vin_sys_5v0_j_per_45_output_tokens']<row['median_vin_sys_5v0_j_per_45_output_tokens']) for x in peers)
(HERE/'pareto-cells.json').write_text(json.dumps({'scope':'Within each identical workload and KV cell; request latency versus separate VIN_SYS_5V0 request-window J per fixed 45 output tokens. Named rail includes board idle/background, is not process-attributed and is not whole-device energy.','cells':summary},indent=2)+'\n')
with (HERE/'pareto-cells.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]),lineterminator='\n');w.writeheader();w.writerows(summary)
# Faceted scatter plot, four independent comparisons; no cross-workload ranking.
W,H=1200,760; panel_w,panel_h=550,300; offsets=[(55,100),(635,100),(55,430),(635,430)]
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>','<text x="50" y="35" font-family="sans-serif" font-size="24" font-weight="bold">Cell-scoped latency / named-rail energy diagnostics</text>','<text x="50" y="61" font-family="sans-serif" font-size="14" fill="#444">x = median client total seconds; y = VIN_SYS_5V0 J per 45 output tokens. Labels show decode TPS and minimum admission GiB; lower is better.</text>']
colors={0:'#2563eb',4:'#d97706'}
for idx,(kv,wl) in enumerate([(k,w) for w in sorted({r['workload'] for r in campaign['runs']}) for k in ('fp16','int8')]):
 x0,y0=offsets[idx]; group=[r for r in summary if r['kv']==kv and r['workload']==wl]
 xvals=[r['median_client_total_s'] for r in group];yvals=[r['median_vin_sys_5v0_j_per_45_output_tokens'] for r in group]
 xmin,xmax=min(xvals)*.94,max(xvals)*1.06; ymin,ymax=min(yvals)*.94,max(yvals)*1.06
 xL,xR=x0+75,x0+panel_w-35; yT,yB=y0+45,y0+panel_h-70
 sx=lambda v:xL+(v-xmin)/(xmax-xmin)*(xR-xL)
 sy=lambda v:yB-(v-ymin)/(ymax-ymin)*(yB-yT)
 short='512 tokens' if wl.endswith('512') else '7,501 tokens'
 parts.append(f'<text x="{x0}" y="{y0+20}" font-family="sans-serif" font-size="17" font-weight="bold">{kv.upper()} KV · {short}</text>')
 parts.extend([f'<line x1="{xL}" y1="{yB}" x2="{xR}" y2="{yB}" stroke="#333"/>',f'<line x1="{xL}" y1="{yT}" x2="{xL}" y2="{yB}" stroke="#333"/>'])
 for t in (0,1):
  xv=xmin+(xmax-xmin)*t; xx=sx(xv); yv=ymin+(ymax-ymin)*t; yy=sy(yv)
  parts.extend([f'<line x1="{xx}" y1="{yT}" x2="{xx}" y2="{yB}" stroke="#ddd"/>',f'<line x1="{xL}" y1="{yy}" x2="{xR}" y2="{yy}" stroke="#ddd"/>',f'<text x="{xx}" y="{yB+18}" text-anchor="middle" font-family="sans-serif" font-size="11">{xv:.1f}</text>',f'<text x="{xL-9}" y="{yy+4}" text-anchor="end" font-family="sans-serif" font-size="11">{yv:.2f}</text>'])
 parts.append(f'<text x="{(xL+xR)/2}" y="{yB+40}" text-anchor="middle" font-family="sans-serif" font-size="13">Client total time (s)</text>')
 for a,b in zip(group,group[1:]):
  parts.append(f'<line x1="{sx(a["median_client_total_s"])}" y1="{sy(a["median_vin_sys_5v0_j_per_45_output_tokens"])}" x2="{sx(b["median_client_total_s"])}" y2="{sy(b["median_vin_sys_5v0_j_per_45_output_tokens"])}" stroke="#999" stroke-dasharray="4 4"/>')
 for r in group:
  xx,yy=sx(r['median_client_total_s']),sy(r['median_vin_sys_5v0_j_per_45_output_tokens']); col=colors[r['mtp_window']]
  parts.append(f'<circle cx="{xx}" cy="{yy}" r="8" fill="{col}"/>')
  parts.append(f'<text x="{xx+11}" y="{yy-12 if r['mtp_window']==0 else yy+19}" font-family="sans-serif" font-size="12">MTP{r["mtp_window"]} · {r["median_decode_tps"]:.2f} tok/s · {r["minimum_admission_available_gib"]:.2f} GiB min</text>')
parts.extend(['<circle cx="930" cy="735" r="7" fill="#2563eb"/><text x="944" y="740" font-family="sans-serif" font-size="13">MTP off</text>','<circle cx="1030" cy="735" r="7" fill="#d97706"/><text x="1044" y="740" font-family="sans-serif" font-size="13">MTP4</text>','</svg>'])
(HERE/'pareto-latency-energy.svg').write_text('\n'.join(parts)+'\n')
print(json.dumps(summary,indent=2))
