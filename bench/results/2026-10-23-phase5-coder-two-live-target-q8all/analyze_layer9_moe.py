#!/usr/bin/env python3
"""Pair layer-9 MoE records at position 83 by route token and report parts."""
import argparse,json,math,struct
import hashlib
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
root=p.parse_args().run.resolve();H=struct.Struct('<8sIIIIQqii')
def read_blob(path,magic):
 data=path.read_bytes();off=0;out=[]
 while off<len(data):
  if len(data)-off<H.size:raise ValueError(f'{path}: truncated header')
  m,v,l,a,reserved,width,pos,slot,token=H.unpack_from(data,off);off+=H.size
  if m!=magic or v!=2 or l!=9 or reserved:raise ValueError(f'{path}: invalid record')
  k=a if magic==b'STMPART2' else None
  n=(k*width if magic==b'STMPART2' else 2*width)*4
  if len(data)-off<n:raise ValueError(f'{path}: truncated payload')
  payload=data[off:off+n];off+=n
  if magic==b'MOEOUT02':
   out.append({'layer':l,'position':pos,'token':token,'slot':slot,'width':width,
               'shared':payload[:width*4],'payload':payload[width*4:]})
  else:out.append({'layer':l,'position':pos,'token':token,'slot':slot,'k':k,'width':width,'payload':payload})
 return out
def jsonrows(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def metrics(a,b):
 x=struct.unpack(f'<{len(a)//4}f',a);y=struct.unpack(f'<{len(b)//4}f',b);d=[u-v for u,v in zip(x,y)];norm=math.fsum(u*u for u in x)
 return {'values':len(x),'different_values':sum(u!=v for u,v in zip(x,y)),
         'max_abs':max(map(abs,d),default=0),'relative_l2':math.sqrt(math.fsum(v*v for v in d)/norm) if norm else 0.0}
def arm(stem):
 routes=[r for r in jsonrows(root/f'{stem}.routes.jsonl') if r.get('layer')==9 and r.get('position')==83]
 parts=read_blob(root/f'{stem}.parts.stmparts',b'STMPART2');outs=read_blob(root/f'{stem}.output.stmoe',b'MOEOUT02')
 routes=[r for r in routes if r.get('token_id')==11];parts=[r for r in parts if r['position']==83 and r['token']==11];outs=[r for r in outs if r['position']==83 and r['token']==11]
 if len(routes)!=1 or len(parts)!=1 or len(outs)!=1:raise ValueError(f'{stem}: route/parts/output counts {len(routes)}/{len(parts)}/{len(outs)}')
 return routes[0],parts[0],outs[0],jsonrows(root/f'{stem}.owners.jsonl')
sr,sp,so,sowners=arm('serial');br,bp,bo,bowners=arm('batch')
if sp['k']!=bp['k'] or sp['width']!=bp['width']:raise ValueError('part geometry mismatch')
k,w=sp['k'],sp['width']; per=[]
so_row=next((x for x in sowners if x.get('layer')==9 and x.get('position')==83 and x.get('token_id')==11),None)
bo_row=next((x for x in bowners if x.get('layer')==9 and x.get('position')==83 and x.get('token_id')==11 and x.get('ids')==br['ids']),None)
if so_row is None or bo_row is None:raise ValueError('could not pair owner records by route and token')
pack_activation=lambda x:struct.pack(f'<{len(x)}f',*x)
activation_exact=pack_activation(so_row['activation'])==pack_activation(bo_row['activation'])
if not activation_exact:raise ValueError('same-position route activations differ')
for i in range(k):per.append({'expert_id':sr['ids'][i], 'rank':i,
 'serial_owner_code':so_row['route_kind'][i],'batch_owner_code':bo_row['route_kind'][i],
 'owner_changed':so_row['route_kind'][i]!=bo_row['route_kind'][i],
 'serial_vs_batch':metrics(sp['payload'][i*w*4:(i+1)*w*4],bp['payload'][i*w*4:(i+1)*w*4])})
result={'layer':9,'position':83,'token':11,'serial_route':sr,'batch_route':br,
 'routes_equal':sr['ids']==br['ids'] and sr['weights']==br['weights'],
 'expert_parts_bit_identical':sp['payload']==bp['payload'],'per_expert_parts':per,
 'combined_output':metrics(so['payload'],bo['payload']),
 'owner_attribution':{'serial_route_kind':so_row['route_kind'],'batch_route_kind':bo_row['route_kind'],
  'same_input_activation_bitwise_equal':activation_exact,
  'activation_sha256':hashlib.sha256(pack_activation(so_row['activation'])).hexdigest(),
  'serial_row':{'row':so_row['row'],'stream_row':so_row['stream_row'],'n_tok':so_row['n_tok']},
  'batch_row':{'row':bo_row['row'],'stream_row':bo_row['stream_row'],'n_tok':bo_row['n_tok']}},
 'limits':['Only one captured token/position; no general claim.','Owner rows are raw attribution records and are not assigned to a prompt without an exact token/route match.']}
(root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'routes_equal':result['routes_equal'],'expert_parts_bit_identical':result['expert_parts_bit_identical'],
                  'combined_output':result['combined_output'],'owner_attribution':result['owner_attribution'],
                  'changed_experts':[x for x in per if x['owner_changed'] or x['serial_vs_batch']['different_values']]},indent=2))
