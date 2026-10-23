#!/usr/bin/env python3
"""Compare four-request layer-40 residual/hyperconnection boundary captures."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER=struct.Struct('<8sIIQQQii'); N=2560; HC=4
FIELDS={'after_layer_R':HC*N,'after_layer_bo':N,'after_layer_inj2':HC,
        'before_next_read_R':HC*N,'before_next_read_bo':N,'before_next_read_inj2':HC,
        'after_next_read_R':HC*N,'after_next_read_xn':HC*N}

def read(path,layer,position):
 raw=path.read_bytes();off=0;rows=[]
 while off<len(raw):
  magic,version,actual_layer,pos,n,hc,token,reserved=HEADER.unpack_from(raw,off);off+=HEADER.size
  if (magic,version,actual_layer,pos,n,hc,reserved)!=(b'STBNDY1\0',1,layer,position,N,HC,0): raise ValueError(f'invalid boundary header in {path}')
  fields={}
  for name,count in FIELDS.items():
   size=count*4;payload=raw[off:off+size];off+=size
   if len(payload)!=size or not all(math.isfinite(x[0]) for x in struct.iter_unpack('<f',payload)):raise ValueError(f'invalid {name} payload')
   fields[name]=payload
  rows.append({'token':token,'fields':fields})
 if off!=len(raw) or len(rows)!=4:raise ValueError(f'{path}: expected four records, found {len(rows)}')
 return rows

def compare(a,b):
 x=struct.unpack(f'<{len(a)//4}f',a);y=struct.unpack(f'<{len(b)//4}f',b);d=[float(v)-float(w) for v,w in zip(x,y)];den=math.fsum(float(v)**2 for v in y)
 return {'bitwise_equal':a==b,'different_values':sum(v!=w for v,w in zip(x,y)),'max_abs':max(map(abs,d),default=0.0),'relative_l2':math.sqrt(math.fsum(v*v for v in d)/den) if den else None,'left_sha256':hashlib.sha256(a).hexdigest(),'right_sha256':hashlib.sha256(b).hexdigest()}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run-dir',type=Path,default=Path(__file__).resolve().parent);args=ap.parse_args();out={'scope':'verifier residual/hyperconnection boundary after layer 40 at generated position 522','requests':['initial','intermediate','recovery','continuation'],'arms':{}}
 for arm in ('adaptive-cap8','delayed-control'):
  rows=read(args.run_dir/arm/'result/verify-boundary.bin',40,522);trans={}
  for i,j,name in ((0,1,'initial_to_intermediate'),(1,2,'intermediate_to_recovery'),(2,3,'recovery_to_continuation'),(0,2,'initial_to_recovery')):
   if rows[i]['token']!=rows[j]['token']:raise ValueError(f'{arm} token mismatch in {name}')
   trans[name]={field:compare(rows[i]['fields'][field],rows[j]['fields'][field]) for field in FIELDS}
  out['arms'][arm]={'token_id':rows[0]['token'],'transitions':trans}
 path=args.run_dir/'boundary-sequence-analysis.json';path.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({arm:{name:{f:r['bitwise_equal'] for f,r in fields.items()} for name,fields in v['transitions'].items()} for arm,v in out['arms'].items()},indent=2))
if __name__=='__main__':main()
