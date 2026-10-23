#!/usr/bin/env python3
"""Compare each selected layer-10 committed-state record by position and token."""
import argparse,json,math,struct
from array import array
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
root=p.parse_args().run.resolve();H=struct.Struct('<8sIiqQQii')
def read(path):
 rows=[]
 with path.open('rb') as f:
  while raw:=f.read(H.size):
   if len(raw)!=H.size:raise ValueError('truncated header')
   magic,version,layer,pos,rec,count,token,slot=H.unpack(raw);payload=f.read(count*4)
   if magic!=b'STGCMT1\0' or version!=1 or layer!=10 or len(payload)!=count*4:raise ValueError('bad capture row')
   a=array('f');a.frombytes(payload);rows.append({'position':pos,'recurrent':rec,'token':token,'slot':slot,'values':a})
 return rows
serial=read(root/'serial.stgcmt');batch=read(root/'batch.stgcmt')
result=[]
for s in serial:
 candidates=[b for b in batch if b['position']==s['position'] and b['token']==s['token']]
 if len(candidates)!=1:
  result.append({'position':s['position'],'token':s['token'],'batch_candidates':len(candidates),'status':'ambiguous_or_missing'});continue
 b=candidates[0]
 def metric(start,end):
  a=s['values'][start:end];z=b['values'][start:end];ds=[x-y for x,y in zip(a,z)]
  norm=math.fsum(x*x for x in a);err=math.fsum(x*x for x in ds)
  return {'values':len(ds),'different_values':sum(x!=0 for x in ds),'max_abs':max(map(abs,ds),default=0),
          'relative_l2':math.sqrt(err/norm) if norm else 0.0}
 result.append({'position':s['position'],'input_token':s['token'],'batch_slot':b['slot'],'status':'paired',
                'recurrent':metric(0,s['recurrent']),'convolution':metric(s['recurrent'],len(s['values']))})
summary={'layer':10,'comparisons':result,
         'first_position_with_recurrent_difference':next((r['position'] for r in result if r.get('status')=='paired' and r['recurrent']['different_values']),None),
         'limits':['Sparse position sample; first changed point is bounded only by adjacent captured positions.',
                   'Pairs rows by absolute position and input token; prompt identity must be unique at each selected position.']}
(root/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
