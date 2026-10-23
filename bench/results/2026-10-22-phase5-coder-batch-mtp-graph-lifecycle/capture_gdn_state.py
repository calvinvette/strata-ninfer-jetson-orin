#!/usr/bin/env python3
"""Capture committed GDN state at L=127 in serial and two-slot batch paths."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-state-L127'
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

def arm_args(mtp):
    args=list(base_args)
    if not mtp:
        for key in ('--mtp','--mtp-max-t'): remove_arg(args,key)
    return args

def mk_env(name, batch, mtp):
    env=dict(base_env)
    env.update({'STRATA_STATE_HASH':'1','STRATA_ACCEPTED_PREFIX_TRACE':'1',
                'STRATA_PREFILL_CPU_SHARE':'0'})
    if batch:
        env.update({'STRATA_BATCH_GDN_DUMP_AT':'127',
                    'STRATA_BATCH_GDN_DUMP_PATH':str((OUT/(name+'-batch-gdn')).resolve())})
    else:
        env.update({'STRATA_STATE_DUMP_GDN_AT':'127',
                    'STRATA_STATE_DUMP_GDN':str((OUT/(name+'-serial-gdn.bin')).resolve())})
    return env

def generate(engine,prompt):
    tokens=[x for x in engine.generate(prompt,96,{'temperature':0},threading.Event()) if x is not None]
    return {'tokens':tokens,'finish':engine.last.get('finish')}

def serial(name,mtp):
    eng=StrataEngine(CFG['exe'],arm_args(mtp),cwd=CFG.get('cwd'),log=str(OUT/(name+'-serial.log')),
                     env=mk_env(name,False,mtp))
    try: return generate(eng,prompts['slot-1'])
    finally: eng.close()

def batch(name,mtp):
    args=arm_args(mtp)+['--batch','2']
    if mtp: args.append('--batch-mtp')
    eng=StrataEngine(CFG['exe'],args,cwd=CFG.get('cwd'),log=str(OUT/(name+'-batch.log')),
                     env=mk_env(name,True,mtp))
    try:
        if eng.batch!=2: raise RuntimeError(f'{name}: only admitted {eng.batch} slots')
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(generate,eng,prompts[k]) for k in prompts]
            values=[job.result() for job in jobs]
        return {'request-0':values[0],'request-1':values[1]}
    finally: eng.close()

outputs={}
for name,mtp in [('target-only',False),('mtp2',True)]:
    outputs[name+'-serial']=serial(name,mtp)
    outputs[name+'-batch']=batch(name,mtp)
(OUT/'result.json').write_text(json.dumps({'position':127,'state_length':127,'prompt':prompts['slot-1'],
                                           'outputs':outputs},indent=2)+'\n')
print(json.dumps({name:len(values['tokens']) if 'tokens' in values else {k:len(v['tokens']) for k,v in values.items()}
                  for name,values in outputs.items()}))
