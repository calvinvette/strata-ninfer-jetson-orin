#!/usr/bin/env python3
"""Compare layer-12 verifier routes, expert parts and combined MoE output."""
import json
import struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=struct.Struct('<8sIIIIQq8i')

def read(path,kind):
    raw=path.read_bytes(); off=0; rows=[]
    while off<len(raw):
        magic,version,layer,count,k,width,pos,*tokens=H.unpack_from(raw,off); off+=H.size
        if magic!=(b'STMPART1' if kind=='parts' else b'STMOEOUT') or version!=1 or layer!=12 or count!=1 or pos!=512:
            raise ValueError(f'invalid layer-12 {kind} capture')
        size=(k*width if kind=='parts' else 2*width)*4
        rows.append({'token':tokens[0],'k':k,'width':width,'payload':raw[off:off+size]});off+=size
    if len(rows)!=3 or off!=len(raw): raise ValueError(f'expected three position-512 {kind} records')
    return rows

def main():
    out={'scope':'layer-12 position-512 verifier MoE rows across three same-service requests','arms':{}}
    for arm in ('delayed-control','adaptive-cap8'):
        run=HERE/arm/'result'
        routes=[json.loads(x) for x in (run/'verify-moe-routes.jsonl').read_text().splitlines()][1:]
        parts=read(run/'verify-moe-parts.bin','parts'); outputs=read(run/'verify-moe-output.bin','output')
        if len(routes)!=3: raise ValueError('expected three route records')
        rows=[]
        for route,part,output in zip(routes,parts,outputs):
            if route['layer']!=12 or route['position']!=512 or route['token_id']!=part['token'] or part['token']!=output['token']:
                raise ValueError('route/output identity mismatch')
            rows.append({'token_id':route['token_id'],'ids':route['ids'],'weights':route['weights'],
                         'parts':part['payload'],'output':output['payload'],'width':part['width'],'k':part['k']})
        transitions=[]
        for i,j in ((0,1),(1,2)):
            a,b=rows[i],rows[j]
            transitions.append({'requests':[i,j],'token_equal':a['token_id']==b['token_id'],
                'ids_equal':a['ids']==b['ids'],'weights_equal':a['weights']==b['weights'],
                'expert_parts_bit_identical':a['parts']==b['parts'],
                'per_expert_differing_f32_values':[sum(x!=y for x,y in zip(struct.unpack('<%df'%a['width'],a['parts'][q*a['width']*4:(q+1)*a['width']*4]),struct.unpack('<%df'%b['width'],b['parts'][q*b['width']*4:(q+1)*b['width']*4]))) for q in range(a['k'])],
                'shared_and_combined_bit_identical':a['output']==b['output']})
        out['arms'][arm]={'transitions':transitions}
    (HERE/'layer12-moe-analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    for arm,a in out['arms'].items():print(arm,a['transitions'])
if __name__=='__main__':main()
