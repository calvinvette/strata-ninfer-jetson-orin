#!/usr/bin/env python3
"""Validate and summarize the current-binary all-layer adaptive pair."""
import gzip, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CAMPAIGN=Path(__file__).resolve().parent/'all-layer-pair'

def read_trace(path):
    layers={}
    with gzip.open(path,'rt') as f:
        header=json.loads(next(f))
        if header.get('format')!='strata-moe-dispatch-v2' or header.get('n_embd')!=2560:
            raise RuntimeError(f'unexpected trace header: {header}')
        for line in f:
            row=json.loads(line)
            layers.setdefault(row['layer'],[]).append(row)
    if set(layers)!=set(range(48)):
        raise RuntimeError(f'expected all 48 layers; got {sorted(layers)}')
    return layers

def compare(a,b,capture_row_index=None, require_alignment=True):
    if require_alignment and (a['dispatch']!=b['dispatch'] or a['row']!=b['row'] or a['n_tok']!=b['n_tok']):
        raise RuntimeError('paired all-layer rows are not aligned by dispatch/row/window')
    if len(a['activation'])!=2560 or len(b['activation'])!=2560:
        raise RuntimeError('unexpected activation width')
    common=set(a['ids'])&set(b['ids'])
    ak=dict(zip(a['ids'],a['route_kind'])); bk=dict(zip(b['ids'],b['route_kind']))
    owners=[{'expert':e,'control':ak[e],'candidate':bk[e]} for e in sorted(common) if ak[e]!=bk[e]]
    return {'dispatch':a['dispatch'],'layer':a['layer'],'row':a['row'],'capture_row_index':capture_row_index,
            'activation_different_values':sum(x!=y for x,y in zip(a['activation'],b['activation'])),
            'expert_ids_equal':a['ids']==b['ids'],'owner_changes':owners}

def first_hit(records, key, predicate):
    hits=[r for r in records if predicate(r)]
    return min(hits,key=lambda r:(r['dispatch'],r['row'],r['layer'])) if hits else None

def summarize(control, candidate, lo, hi):
    rows=[]
    for layer in range(48):
        aa=control[layer][lo:hi]; bb=candidate[layer][lo:hi]
        if len(aa)!=len(bb): raise RuntimeError(f'layer {layer}: unequal paired row counts')
        rows.extend(compare(x,y,lo+i) for i,(x,y) in enumerate(zip(aa,bb)))
    out={}
    for label, pred in (
        ('first_owner_difference',lambda r:bool(r['owner_changes'])),
        ('first_activation_difference',lambda r:r['activation_different_values']>0),
        ('first_expert_id_difference',lambda r:not r['expert_ids_equal'])):
        hit=first_hit(rows,label,pred)
        out[label]=hit
    out['paired_rows']=len(rows)
    out['rows_with_activation_differences']=sum(r['activation_different_values']>0 for r in rows)
    out['rows_with_expert_id_differences']=sum(not r['expert_ids_equal'] for r in rows)
    out['same_expert_owner_change_count']=sum(len(r['owner_changes']) for r in rows)
    return out

def main():
    campaign=json.loads((CAMPAIGN/'campaign.json').read_text())
    if campaign['status']!='pass' or campaign['order']!=['delayed-control','adaptive-cap8']:
        raise RuntimeError('campaign status/order mismatch')
    runs={r['name']:r for r in campaign['runs']}
    arms={name:read_trace(CAMPAIGN/name/'result/all-layers.jsonl.gz') for name in runs}
    for name,run in runs.items():
        analysis=run['analysis']
        if run['supervisor_status']!='pass' or analysis['binary_sha256']!=campaign['binary_sha256']:
            raise RuntimeError(f'{name}: supervisor or binary identity mismatch')
        if analysis['captured_rows']!=4096 or len(analysis['requests'])!=4:
            raise RuntimeError(f'{name}: incomplete capture/request set')
        if min(int(v) for v in analysis['layer_row_counts'].values())<85:
            raise RuntimeError(f'{name}: insufficient per-layer coverage')
        supervisor=json.loads((CAMPAIGN/name/'supervisor/result.json').read_text())
        if min(supervisor['minimum_available_bytes'],supervisor['minimum_admission_available_bytes'])<6*2**30:
            raise RuntimeError(f'{name}: six-GiB floor breached')
        events={}
        for line in (CAMPAIGN/name/'supervisor/memory.jsonl').read_text().splitlines():
            sample=json.loads(line)
            for cg in sample.get('cgroups',[]):
                for key,value in cg.get('memory_events',{}).items(): events[key]=max(events.get(key,0),value)
        if any(events.values()): raise RuntimeError(f'{name}: cgroup memory events: {events}')
    segments={'initial-short-512':(0,22),'long-2048':(22,44),
              'recovery-short-512':(44,66),'continuation-short-512':(66,85)}
    comparisons={name:summarize(arms['delayed-control'],arms['adaptive-cap8'],*bounds)
                 for name,bounds in segments.items()}
    control=json.loads((CAMPAIGN/'delayed-control/result/requests.json').read_text())['requests']
    candidate=json.loads((CAMPAIGN/'adaptive-cap8/result/requests.json').read_text())['requests']
    if [x['name'] for x in control]!=[x['name'] for x in candidate]:
        raise RuntimeError('request order differs')
    token_differences={x['name']:sum(a!=b for a,b in zip(x['ids'],y['ids']))
                       for x,y in zip(control,candidate)}
    state_differences={x['name']:[k for k in x['state'] if x['state'][k]!=y['state'][k]]
                       for x,y in zip(control,candidate)}
    within={}
    for name in runs:
        req=json.loads((CAMPAIGN/name/'result/requests.json').read_text())['requests']
        within_rows=[]
        for layer in range(48):
            aa=arms[name][layer][0:22]; bb=arms[name][layer][44:66]
            within_rows.extend(compare(x,y,i,require_alignment=False) for i,(x,y) in enumerate(zip(aa,bb)))
        within[name]={'recovery_token_differences_vs_initial':sum(a!=b for a,b in zip(req[0]['ids'],req[2]['ids'])),
          'recovery_state_changed_fields_vs_initial':[k for k in req[0]['state'] if req[0]['state'][k]!=req[2]['state'][k]],
          'continuation_token_differences_vs_initial':sum(a!=b for a,b in zip(req[0]['ids'],req[3]['ids'])),
          'first_initial_vs_recovery_owner_difference':first_hit(within_rows,'owner',lambda r:bool(r['owner_changes'])),
          'first_initial_vs_recovery_activation_difference':first_hit(within_rows,'activation',lambda r:r['activation_different_values']>0),
          'first_initial_vs_recovery_expert_id_difference':first_hit(within_rows,'expert',lambda r:not r['expert_ids_equal'])}
    result={'campaign_status':campaign['status'],'seed':campaign['seed'],'order':campaign['order'],
      'binary_sha256':campaign['binary_sha256'],'repository_head':campaign['repository_head'],
      'model_repository':campaign['model_repository'],'model_revision':campaign['model_revision'],
      'quantization':campaign['quantization'],'cross_arm_token_differences':token_differences,
      'cross_arm_state_differing_fields':state_differences,'within_arm':within,
      'all_layer_rows_by_request':{k:v['paired_rows'] for k,v in comparisons.items()},
      'all_layer_comparisons':comparisons,
      'capture_limit':'4096 rows; first three 22-row request groups complete at all 48 layers; continuation group has first 19 rows per layer (20 on layers 0-15)',
      'physical_memory_floor_and_cgroup_events_checked':True,
      'limits':['diagnostic activations are formatted to %.9g','route ownership changes and later activation differences support a mechanism but do not alone prove the complete service-level causal path','no performance, energy or task-quality claim']}
    (CAMPAIGN/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'token_differences':token_differences,'within_arm':within,
      'first_owner_difference':{k:v['first_owner_difference'] for k,v in comparisons.items()},
      'first_activation_difference':{k:v['first_activation_difference'] for k,v in comparisons.items()}},indent=2))

if __name__=='__main__': main()
