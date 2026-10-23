#!/usr/bin/env python3
"""Compare layer-10 GDN state at a selected position by matching input token."""
import json,math,struct,argparse
from array import array
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,default=Path(__file__).resolve().parent/'layer10-prestate-132')
p.add_argument('--position',type=int,default=132)
p.add_argument('--batch-slot',type=int,default=-1)
opts=p.parse_args();root=opts.run.resolve();header=struct.Struct('<8sIiqQQii')
def records(path):
 out=[]
 with path.open('rb') as f:
  while raw:=f.read(header.size):
   if len(raw)!=header.size:raise ValueError(f'{path}: truncated record header')
   magic,version,layer,pos,recurrent,count,token,slot=header.unpack(raw)
   payload=f.read(count*4)
   if magic!=b'STGCMT1\0' or version!=1 or layer!=10 or pos!=opts.position or len(payload)!=count*4:raise ValueError(f'{path}: invalid capture')
   values=array('f');values.frombytes(payload)
   out.append({'layer':layer,'position':pos,'recurrent':recurrent,'token':token,'slot':slot,'values':values})
 return out

serial=records(root/'serial.stgcmt');batch=records(root/'batch.stgcmt')
if len(serial)!=1:raise ValueError(f'expected one serial record, got {len(serial)}')
matches=[r for r in batch if r['token']==serial[0]['token'] and (opts.batch_slot<0 or r['slot']==opts.batch_slot)]
if len(matches)!=1:raise ValueError(f'expected one batch row with token {serial[0]["token"]}, got {len(matches)}')
a,b=serial[0],matches[0]
def metric(start,end):
 av=a['values'][start:end];bv=b['values'][start:end];ds=[x-y for x,y in zip(av,bv)]
 norm=math.fsum(x*x for x in av);err=math.fsum(x*x for x in ds)
 return {'values':len(ds),'different_values':sum(x!=0 for x in ds),'max_abs':max(map(abs,ds),default=0.0),
         'relative_l2':math.sqrt(err/norm) if norm else 0.0}
result={'layer':10,'position':opts.position,'serial_input_token':a['token'],'batch_input_token':b['token'],'batch_slot':b['slot'],
        'recurrent':metric(0,a['recurrent']),'convolution':metric(a['recurrent'],len(a['values'])),
        'whole_state':metric(0,len(a['values']))}
(root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
