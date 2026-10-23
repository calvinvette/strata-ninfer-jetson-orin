#!/usr/bin/env python3
"""Compare layer-10 GDN stages for the serial and batch slot-1 rows."""
import hashlib
import json
import math
import argparse
from pathlib import Path
import struct

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', type=Path, default=Path(__file__).resolve().parent/'layer10-position-133')
parser.add_argument('--position', type=int, default=133)
parser.add_argument('--layer', type=int, default=10)
parser.add_argument('--output', type=Path, help='analysis JSON path; defaults to <run>/analysis.json')
parser.add_argument('--batch-slot', type=int, default=-1,
                    help='disambiguate repeated input tokens using the verifier slot; -1 requires a unique match')
args=parser.parse_args()
ROOT = args.run.resolve()
HEADER = struct.Struct('<8sIiiqQQQQQ8q8i8i')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')

def records(path):
    data=path.read_bytes(); off=0; out=[]
    while off<len(data):
        if off+HEADER.size>len(data): raise ValueError(f'{path}: truncated header')
        h=HEADER.unpack_from(data,off); magic,version,layer,rows,pos0,n,c,hv,zv,state=h[:10]
        positions,slots,tokens=h[10:18],h[18:26],h[26:34]
        if magic!=b'STGDIAG5' or version!=5 or layer!=args.layer or n!=2560 or rows<=0:
            raise ValueError(f'{path}: unexpected header {h[:10]}')
        off+=HEADER.size
        for row in range(rows):
            fields={}
            # GdnDiagOffsets lays out each field as a contiguous array of rows;
            # fields are not interleaved row by row.
            field_base=0
            for name,count in zip(FIELDS,(n,c,c,hv,hv,zv,zv,n,n,n)):
                size=count*4
                start=off+field_base+row*size
                fields[name]=data[start:start+size]
                field_base+=rows*size
            out.append({'position':positions[row],'slot':slots[row],'token':tokens[row],
                        'dims':{'n':n,'c':c,'hv':hv,'zv':zv},'fields':fields})
        off+=rows*(4*n+2*c+2*hv+2*zv)*4
    return out

all_rows=records(ROOT/'serial.stgdiag')+records(ROOT/'batch.stgdiag')
serial=[x for x in all_rows if x['position']==args.position and x['slot']==-1]
if len(serial)!=1:
    raise ValueError(f'expected one serial row, got {len(serial)}')
# The service request names do not define verifier row IDs. Pair the batch row by
# the input token and absolute position, then report its actual diagnostic slot.
batch=[x for x in all_rows if x['position']==args.position and x['slot']>=0 and x['token']==serial[0]['token']]
if args.batch_slot >= 0:
    batch=[x for x in batch if x['slot']==args.batch_slot]
if len(batch)!=1:
    raise ValueError(f'expected one batch row for input token {serial[0]["token"]}, got {len(batch)}')
comparison={}
for field in FIELDS:
    a=struct.unpack(f'<{len(serial[0]["fields"][field])//4}f',serial[0]['fields'][field])
    b=struct.unpack(f'<{len(batch[0]["fields"][field])//4}f',batch[0]['fields'][field])
    delta=[x-y for x,y in zip(a,b)]; denom=math.sqrt(math.fsum(x*x for x in a))
    comparison[field]={'values':len(a),'different_values':sum(x!=y for x,y in zip(a,b)),
                       'max_abs':max(map(abs,delta),default=0.0),
                       'relative_l2':math.sqrt(math.fsum(x*x for x in delta))/denom if denom else 0.0,
                       'serial_sha256':hashlib.sha256(serial[0]['fields'][field]).hexdigest(),
                       'batch_sha256':hashlib.sha256(batch[0]['fields'][field]).hexdigest()}
result={'layer':args.layer,'position':args.position,'input_token':serial[0]['token'],'batch_slot':batch[0]['slot'],
        'dimensions':serial[0]['dims'],
        'first_different_field':next((f for f in FIELDS if comparison[f]['different_values']),None),
        'fields':comparison,
        'limits':['Single layer/position diagnostic; does not capture the upstream layer-10 input chain.',
                  'No performance or general correctness claim.']}
output = args.output.resolve() if args.output else ROOT/'analysis.json'
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'layer':args.layer,'position':args.position,'input_token':result['input_token'],'batch_slot':result['batch_slot'],
                  'first_different_field':result['first_different_field'],
                  'fields':{k:{'different_values':v['different_values'],'max_abs':v['max_abs'],
                               'relative_l2':v['relative_l2']} for k,v in comparison.items()}},indent=2))
