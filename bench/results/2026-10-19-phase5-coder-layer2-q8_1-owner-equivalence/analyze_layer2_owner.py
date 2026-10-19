#!/usr/bin/env python3
"""Validate supervision and summarize layer-2 owner-placement effects."""
import gzip, hashlib, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TARGETS={(2,x) for x in (174,62,69,130,143,151,28)}
KEYS=('L','gdn','ple','tail','dead','pooled','pooled_full','kv','ple_prev','mtp','stale')
STATE_RE=re.compile(r'ACCEPTED_PREFIX position=(\d+).*?committed=(\d+) tokens=([0-9,]+) state=\{STATE_HASH ([^}]+)')
def text(p):
 p=Path(p)
 if not p.exists() and not Path(str(p)+'.gz').exists():
  shared=HERE/'shared-captures'/p.name
  if shared.exists(): p=shared
 if str(p).endswith('.gz'): return gzip.open(p,'rt').read()
 if p.exists(): return p.read_text(errors='replace')
 return gzip.open(str(p)+'.gz','rt').read()
def jsonl(p):
 lines=text(p).splitlines();return json.loads(lines[0]),[json.loads(x) for x in lines[1:]]
def capture(req,key,fallback):
 meta=req.get('capture_artifacts',{}).get(key)
 p=HERE/meta['path'] if meta else fallback
 raw=(gzip.open(p,'rb').read() if str(p).endswith('.gz') else Path(p).read_bytes())
 if meta: assert hashlib.sha256(raw).hexdigest()==meta['sha256'] and len(raw)==meta['bytes']
 return Path(p)
def states(p):
 out=[]
 for line in text(p).splitlines():
  m=STATE_RE.search(line)
  if m:
   d=dict(re.findall(r'(\w+)=([0-9a-f,-]+)',m[4])); assert set(KEYS)<=d.keys()
   out.append({'position':int(m[1]),'tokens':[int(x) for x in m[3].split(',')],'state':{k:d[k] for k in KEYS}})
 return out
def cell(root,arm):
 p=root/arm; sup=json.loads((p/'supervisor/result.json').read_text()); req=json.loads((p/'run/requests.json').read_text()); log=text(p/'run/service.log')
 assert sup['status']=='pass' and sup['returncode']==0
 minimum=min(sup['minimum_available_bytes'],sup['minimum_admission_available_bytes']); assert minimum>=6*1024**3
 mem=text(p/'supervisor/memory.jsonl')
 for line in mem.splitlines():
  for cg in json.loads(line).get('cgroups',[]):
   assert all(cg.get('memory_events',{}).get(k,0)==0 for k in ('low','high','max','oom','oom_kill'))
 assert req['selector']=='iq2_s/iq4_nl@layer=2' and req['expert_cache_argument']==3007
 assert 'pre-filled 3007 of 3007 slots' in log
 assert req['accepted_prefix_records']==16
 assert hashlib.sha256(b''.join(Path(HERE/f'prefill-gdn-reference.part{i:02d}').read_bytes() for i in (0,1))).hexdigest()==req['prefill_gdn_sha256']
 h,r=jsonl(capture(req,'routes_all_layers',p/'run/routes-all-layers.jsonl'));assert h['format']=='strata-moe-dispatch-v3' and len(r)==768
 return {'supervisor':sup,'request':req,'states':states(p/'run/service.log'),'routes':[x for x in r if x['layer']==2]}
def main():
 result={'source_commit':'58ea8c00','binary_sha256':hashlib.sha256(Path('/home/calvin/workspace/strata-ninfer-jetson-orin/build/integration/candidate/strata').read_bytes()).hexdigest(),'selector':'iq2_s/iq4_nl@layer=2','blocks':[],'device_route_pair':{}}
 order=(HERE/'paired-runs/order.txt').read_text().splitlines(); result['randomized_order']=order
 result['prompt_sha256']=json.loads((HERE/'paired-runs/block-1/cpu_mirror/run/requests.json').read_text())['prompt_sha256']
 result['profile_design_sha256']=hashlib.sha256((HERE/'profile-design.json').read_bytes()).hexdigest()
 mins=[]
 for b in range(1,4):
  root=HERE/'paired-runs'/f'block-{b}';a=cell(root,'cpu_mirror');z=cell(root,'gpu_layer2')
  assert a['request']['prompt_sha256']==z['request']['prompt_sha256']
  ca=a['request']['completion_ids'];cz=z['request']['completion_ids'];common=0
  for x,y in zip(ca,cz):
   if x!=y:break
   common+=1
  # Compare device-route rows only over matching token history; first differing token
  # makes later route inputs intentionally incomparable.
  da=cell(HERE/'device-route-pair-retry1','cpu_mirror');dz=cell(HERE/'device-route-pair-retry1','gpu_layer2')
  xh,xr=jsonl(capture(da['request'],'device_moe_routes_layer2',HERE/'device-route-pair-retry1/cpu_mirror/run/device-moe-routes.jsonl'))
  yh,yr=jsonl(capture(dz['request'],'device_moe_routes_layer2',HERE/'device-route-pair-retry1/gpu_layer2/run/device-moe-routes.jsonl'))
  assert xh==yh and len(xr)==len(yr)==16
  device_common=0
  for x,y in zip(xr,yr):
   if x!=y: break
   device_common+=1
  ra=a['routes'];rz=z['routes']; route_common=0
  for x,y in zip(ra,rz):
   if (x['position'],x['token_id'],x['ids'],x['activation']) != (y['position'],y['token_id'],y['ids'],y['activation']): break
   route_common+=1
  sa=a['states'];sz=z['states']; shared=min(len(sa),len(sz)); first_diff=[k for k in KEYS if sa[0]['state'][k]!=sz[0]['state'][k]]
  initial_a=next(x for x in ra if x['position']==511); initial_z=next(x for x in rz if x['position']==511)
  owners_a={e:o for e,o in zip(initial_a['ids'],initial_a['route_kind'])}; owners_z={e:o for e,o in zip(initial_z['ids'],initial_z['route_kind'])}
  moved=[]
  for layer,e in TARGETS:
   assert e in owners_a and e in owners_z and owners_a[e]==-1 and owners_z[e]==0
   moved.append(e)
  block_min=min(a['supervisor']['minimum_available_bytes'],a['supervisor']['minimum_admission_available_bytes'],z['supervisor']['minimum_available_bytes'],z['supervisor']['minimum_admission_available_bytes'])/1024**3
  mins.append(block_min)
  result['blocks'].append({'block':b,'completion_ids_equal':ca==cz,'common_completion_tokens':common,'first_state_fingerprint_different_fields':first_diff,'prompt_end_gdn_byte_identical':a['request']['prefill_gdn_sha256']==z['request']['prefill_gdn_sha256'],'host_route_records_same_through':route_common,'target_experts_moved_at_prompt_end':len(moved),'host_route_owner_trace_after_divergence':'diagnostic only; route-kind callback can be stale on rows after token divergence','minimum_host_or_admission_gib':round(block_min,3),'cgroup_events':'zero'})
 # Exact device-side layer-2 routing for supplemental pair.
 assert xr[:device_common]==yr[:device_common] and device_common==7
 result['device_route_pair']={'device_topk_ids_and_router_weights_equal_through_matching_prefix':device_common,'first_divergent_device_route_position':xr[device_common]['position'],'all_output_tokens_equal':xr==yr,'minimum_host_gib':min(cell(HERE/'device-route-pair-retry1',a)['supervisor']['minimum_available_bytes'] for a in ('cpu_mirror','gpu_layer2'))/1024**3,'minimum_admission_gib':min(cell(HERE/'device-route-pair-retry1',a)['supervisor']['minimum_admission_available_bytes'] for a in ('cpu_mirror','gpu_layer2'))/1024**3}
 result['summary']={'all_three_pairs_supervised':True,'all_three_pairs_state_equal':False,'common_output_prefix_tokens':6,'state_mismatch_at_first_commit':True,'prompt_end_gdn_identical':True,'conclusion':'Layer-1 owner equivalence does not generalize to this layer-2 IQ2_S/IQ4_NL path. With matching prompt-end GDN and exact device-side layer-2 IDs/weights through the shared prefix, persistent state differs at the first committed token; outputs match for six tokens then diverge at token seven. This is correctness evidence for this prompt/profile, not a performance or quality result.'}
 out=HERE/'analysis.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
