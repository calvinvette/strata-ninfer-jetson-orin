#!/usr/bin/env python3
"""Capture serial and two-live layer-39 owner/parts at position 104."""
import argparse, json, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, remove_arg, replace_arg
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--profile',type=Path,required=True)
p.add_argument('--position',type=int,default=104)
p.add_argument('--layer',type=int,default=39)
p.add_argument('--max-tokens',type=int,default=48)
o=p.parse_args(); out=o.output.resolve(); out.mkdir(parents=True,exist_ok=False)
base=ROOT/'bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle'
cfg=json.loads((base/'config.json').read_text()); args=list(cfg['args'])
for key in ('--mtp','--mtp-max-t','--adapt-every','--adapt-accepted-only'): remove_arg(args,key)
replace_arg(args,'--spec','2'); replace_arg(args,'--max-context','1024'); replace_arg(args,'--expert-cache','1500'); replace_arg(args,'--prompt-cache','6'); replace_arg(args,'--expert-profile',str(o.profile.resolve()))
prompts=prepared_prompts(cfg,2)
def env_for(stem,batch):
 e=child_env(cfg); e.update({'STRATA_NATIVE_CPU_Q8_1_DOT':'all','STRATA_IQ_MT_MIN':'1','STRATA_PREFILL_CPU_SHARE':'0',
 'STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER':str(o.layer),'STRATA_VERIFY_DUMP_MOE_ROUTE_POSITIONS':str(o.position),'STRATA_VERIFY_DUMP_MOE_ROUTE_BATCH':'1','STRATA_VERIFY_DUMP_MOE_ROUTE_PATH':str((out/f'{stem}.routes.jsonl').resolve()),
 'STRATA_VERIFY_DUMP_MOE_PARTS_LAYER':str(o.layer),'STRATA_VERIFY_DUMP_MOE_PARTS_POSITIONS':str(o.position),'STRATA_VERIFY_DUMP_MOE_PARTS_BATCH':'1','STRATA_VERIFY_DUMP_MOE_PARTS_PATH':str((out/f'{stem}.parts.stmparts').resolve()),
 'STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER':str(o.layer),'STRATA_VERIFY_DUMP_MOE_OUTPUT_POSITIONS':str(o.position),'STRATA_VERIFY_DUMP_MOE_OUTPUT_BATCH':'1','STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH':str((out/f'{stem}.output.stmoe').resolve()),
 'STRATA_CAPTURE_MOE_PATH':str((out/f'{stem}.owners.jsonl').resolve()),'STRATA_CAPTURE_MOE_LAYER':str(o.layer),'STRATA_CAPTURE_MOE_POSITIONS':str(o.position),'STRATA_CAPTURE_MOE_ROWS':'64'})
 if batch:e['STRATA_INTEGRATION_TRACE']='1'
 return e
def generate(engine,key): return [int(t) for t in engine.generate(prompts[key],o.max_tokens,{'temperature':0},threading.Event()) if t is not None]
serial=StrataEngine(cfg['exe'],args,cwd=cfg.get('cwd'),log=str(out/'serial.log'),env=env_for('serial',False))
try: serial_tokens=generate(serial,'slot-1')
finally: serial.close()
batch=StrataEngine(cfg['exe'],args+['--batch','2'],cwd=cfg.get('cwd'),log=str(out/'batch.log'),env=env_for('batch',True))
try:
 if batch.batch!=2: raise RuntimeError(f'expected two batch slots, got {batch.batch}')
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={k:pool.submit(generate,batch,k) for k in prompts}; batch_tokens={k:f.result() for k,f in futures.items()}
finally: batch.close()
result={'layer':o.layer,'position':o.position,'max_tokens':o.max_tokens,'serial_slot_1':serial_tokens,'batch':batch_tokens,'prompts':prompts,'profile':{'expert_profile':str(o.profile),'expert_profile_sha256':__import__('hashlib').sha256(o.profile.read_bytes()).hexdigest(),'live_requests':2,'mtp':False,'expert_cache_slots':1500}}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'position':o.position,'serial_tokens':len(serial_tokens),'batch_tokens':{k:len(v) for k,v in batch_tokens.items()}}))
