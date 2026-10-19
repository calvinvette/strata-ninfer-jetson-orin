#!/usr/bin/env python3
"""Check grouped Q8_1 correction owner-pair evidence."""
import argparse, gzip, hashlib, json, re, struct
from pathlib import Path

KEYS = ('gdn','ple','tail','dead','pooled','pooled_full','kv','ple_prev','mtp','stale')
STATE_RE = re.compile(r'ACCEPTED_PREFIX position=(\d+).*?committed=(\d+) tokens=([0-9,]+) state=\{STATE_HASH ([^}]+)')

def state_records(path):
    records=[]
    for match in STATE_RE.finditer(path.read_text(errors='replace')):
        values=dict(re.findall(r'(\w+)=([0-9a-f,-]+)', match[4]))
        if not set(KEYS) <= values.keys():
            raise ValueError(f'incomplete state record in {path}')
        records.append({'position':int(match[1]), 'committed':int(match[2]),
                        'tokens':[int(x) for x in match[3].split(',')],
                        'state':{key:values[key] for key in KEYS}})
    return records

def route_records(path):
    if not path.exists(): path=Path(str(path)+'.gz')
    if path.suffix=='.gz':
        with gzip.open(path,'rt') as stream: lines=stream.read().splitlines()
    else: lines=path.read_text().splitlines()
    header=json.loads(lines[0]); records=[json.loads(line) for line in lines[1:]]
    return header,records

def lines_gzip_aware(path):
    if not path.exists(): path=Path(str(path)+'.gz')
    if path.suffix=='.gz':
        with gzip.open(path,'rt') as stream: return stream.read().splitlines()
    return path.read_text().splitlines()

def shared_capture(base, pattern, expected_bytes, expected_sha):
    digest=hashlib.sha256(); total=0
    for path in sorted((base/'shared-captures').glob(pattern)):
        with gzip.open(path,'rb') as stream:
            while chunk:=stream.read(1024*1024): digest.update(chunk); total+=len(chunk)
    if total!=expected_bytes or digest.hexdigest()!=expected_sha:
        raise ValueError(f'shared capture mismatch for {pattern}: {total} bytes, {digest.hexdigest()}')
    return digest.hexdigest()

def cell(root, block, arm):
    path=root/f'block-{block}'/arm
    result=json.loads((path/'supervisor/result.json').read_text())
    if result['status']!='pass' or result['returncode']!=0:
        raise ValueError(f'failed supervisor: {path}')
    minimum=min(result['minimum_available_bytes'],result['minimum_admission_available_bytes'])
    if minimum < 6*1024**3: raise ValueError(f'headroom floor breach: {path}')
    for line in lines_gzip_aware(path/'supervisor/memory.jsonl'):
        for cg in json.loads(line).get('cgroups',[]):
            if any(cg.get('memory_events',{}).get(k,0) for k in ('low','high','max','oom','oom_kill')):
                raise ValueError(f'cgroup event: {path}')
    req=json.loads((path/'run/requests.json').read_text())
    states=state_records(path/'run/service.log')
    if len(states)!=16 or len(req['completion_ids'])!=16:
        raise ValueError(f'missing accepted-prefix/output records: {path}')
    return {'supervisor':result,'request':req,'states':states,'path':path}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--route-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); blocks=[]; base=Path(__file__).resolve().parent
    shared_capture(base,'prefill-gdn.part*.bin.gz',117669912,'f1e7584f3fb46b8864fdfb79de968e8b0461cbf7584a0fa76f63026929af5a5d')
    accepted_gdn_sha=shared_capture(base,'accepted-prefix-gdn.part*.bin.gz',117669920,'6508db7802f792cdcf146f579c4eb9bbfa26fd6e7f41c0bb3b4a3aa90eca322b')
    with gzip.open(base/'shared-captures/accepted-prefix-gdn.part00.bin.gz','rb') as stream:
        header=stream.read(32)
    if header[:8]!=b'STGDN01\0' or struct.unpack('<QQQ',header[8:])!=(512,36,817152):
        raise ValueError('unexpected first-accepted-prefix GDN dump header')
    dump_identity=json.loads((base/'state-dump-identity.json').read_text())
    if dump_identity['raw_sha256']!=accepted_gdn_sha:
        raise ValueError('raw GDN capture identity manifest mismatch')
    accepted_reqs={}
    for name in ('cpu_mirror','gpu_layer2'):
        path=a.route_root.parent/'postfix-grouped-map-accepted-gdn-pair'/name
        req=json.loads((path/'run/requests.json').read_text())
        log=(path/'run/service.log').read_text(errors='replace')
        if 'STATE_DUMP_GDN' not in log or 'cells=512 layers=36 floats_per_layer=817152' not in log:
            raise ValueError(f'missing direct accepted-prefix GDN dump for {name}')
        accepted_reqs[name]=req
    for block in range(1,4):
        cpu=cell(a.root,block,'cpu_mirror'); gpu=cell(a.root,block,'gpu_layer2')
        cr,gr=cpu['request'],gpu['request']
        if cr['prompt_sha256']!=gr['prompt_sha256'] or cr['prompt_sha256']!=json.loads((cpu['path']/'run/requests.json').read_text())['prompt_sha256']:
            raise ValueError(f'prompt mismatch in block {block}')
        state_equal=cpu['states']==gpu['states']
        if not state_equal: raise ValueError(f'accepted state mismatch in block {block}')
        token_equal=cr['completion_ids']==gr['completion_ids']
        if not token_equal: raise ValueError(f'completion mismatch in block {block}')
        for req in accepted_reqs.values():
            if req['prompt_sha256']!=cr['prompt_sha256'] or req['completion_ids']!=cr['completion_ids']:
                raise ValueError('raw accepted-prefix GDN capture does not match paired prompt and output')
        prefill=[]
        for arm in (cpu,gpu):
            prefill.append(arm['request']['prefill_gdn_sha256'])
        devices=[]
        for name in ('cpu_mirror','gpu_layer2'):
            route_path=a.route_root/name/'run/device-moe-routes.jsonl'
            h,r=route_records(route_path)
            if h!={'format':'strata-verify-moe-route-v1','k':10}: raise ValueError('unexpected device route header')
            if len(r)!=16: raise ValueError('expected 16 device route records')
            route_req=json.loads((a.route_root/name/'run/requests.json').read_text())
            if route_req['prompt_sha256']!=cr['prompt_sha256'] or route_req['completion_ids']!=cr['completion_ids']:
                raise ValueError('device route capture does not match paired prompt and completion')
            devices.append(r)
        if prefill[0]!=prefill[1]: raise ValueError(f'prompt-end GDN mismatch in block {block}')
        if prefill[0]!='f1e7584f3fb46b8864fdfb79de968e8b0461cbf7584a0fa76f63026929af5a5d':
            raise ValueError(f'prompt-end GDN hash not found in shared raw capture, block {block}')
        if devices[0]!=devices[1]: raise ValueError(f'device route mismatch in block {block}')
        order=next(line.split(': ',1)[1] for line in (a.root/'order.txt').read_text().splitlines() if line.startswith(f'block {block} order:'))
        blocks.append({'block':block,'arm_order':order,
                       'prompt_sha256':cr['prompt_sha256'],'accepted_prefix_records_per_arm':16,
                       'accepted_prefix_state_equal':True,'completion_tokens_per_arm':16,'completion_ids_equal':True,
                       'prompt_end_gdn_equal':True,'prompt_end_gdn_sha256':prefill[0],
                       'device_layer2_route_records_per_arm':16,'device_layer2_routes_equal':True,
                       'minimum_host_availability_gib':round(min(cpu['supervisor']['minimum_available_bytes'],gpu['supervisor']['minimum_available_bytes'])/1024**3,3),
                       'minimum_admission_availability_gib':round(min(cpu['supervisor']['minimum_admission_available_bytes'],gpu['supervisor']['minimum_admission_available_bytes'])/1024**3,3)})
    out={'selector':'iq2_s/iq4_nl@layer=2','model_variant':'Coder IQ1_M','expert_cache_argument':3007,
         'accepted_prefix_gdn_raw_sha256':accepted_gdn_sha,
         'blocks':blocks,'result':'all three paired arms had bit-identical accepted-prefix state, completion IDs, prompt-end GDN, and captured device routes'}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__': main()
