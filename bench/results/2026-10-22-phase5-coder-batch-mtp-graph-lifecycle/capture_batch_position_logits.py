#!/usr/bin/env python3
"""Capture full verifier logits at position 127 for both physical batch slots."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-position-127-logits-all-slots'
OUT.mkdir(parents=True, exist_ok=False)
CFG = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
base_args = list(CFG['args'])
replace_arg(base_args, '--spec', '2')
replace_arg(base_args, '--max-context', '1024')
replace_arg(base_args, '--expert-cache', '1500')
replace_arg(base_args, '--prompt-cache', '6')
remove_arg(base_args, '--adapt-every')
remove_arg(base_args, '--adapt-accepted-only')
prompts = prepared_prompts(CFG, 2)
base_env = child_env(CFG)
base_env['STRATA_PREFILL_CPU_SHARE'] = '0'

def engine_args_with_mtp(mtp):
    args = list(base_args)
    if not mtp:
        for key in ('--mtp', '--mtp-max-t'):
            remove_arg(args, key)
    return args

def make_env(name, slot):
    env = dict(base_env)
    env.update({'STRATA_LOGITS_TRACE_POSITION':'127',
                'STRATA_LOGITS_TRACE_SLOT':str(slot),
                'STRATA_LOGITS_TRACE_PATH':str((OUT/(name+'.bin')).resolve())})
    return env

def generate(engine, prompt):
    values = [x for x in engine.generate(prompt, 96, {'temperature':0}, threading.Event()) if x is not None]
    return {'tokens':values,'finish':engine.last.get('finish')}

def serial(name, mtp):
    eng = StrataEngine(CFG['exe'],engine_args_with_mtp(mtp),cwd=CFG.get('cwd'),
                       log=str(OUT/(name+'.log')),env=make_env(name,-1))
    try: return generate(eng,prompts['slot-1'])
    finally: eng.close()

def batch(name, mtp):
    args=engine_args_with_mtp(mtp)+['--batch','2']
    if mtp: args.append('--batch-mtp')
    eng=StrataEngine(CFG['exe'],args,cwd=CFG.get('cwd'),log=str(OUT/(name+'.log')),env=make_env(name,-2))
    try:
        if eng.batch!=2: raise RuntimeError(f'{name}: only admitted {eng.batch} slots')
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(generate,eng,prompts[key]) for key in prompts]
            results=[job.result() for job in jobs]
        return {'slot-0':results[0],'slot-1':results[1]}
    finally: eng.close()

outputs={}
outputs['batch-target-only']=batch('batch-target-only',False)
outputs['batch-mtp2']=batch('batch-mtp2',True)
result={'capture_position':127,'target_slot':1,'target_input_token':11,'prompts':prompts,'outputs':outputs}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({name:arm['finish'] if 'finish' in arm else {k:v['finish'] for k,v in arm.items()} for name,arm in outputs.items()}))
