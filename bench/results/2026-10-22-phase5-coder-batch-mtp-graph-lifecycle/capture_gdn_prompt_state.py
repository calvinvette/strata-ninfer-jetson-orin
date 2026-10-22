#!/usr/bin/env python3
"""Check target-only two-slot committed GDN state just after prompt admission."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from serve.server import StrataEngine,child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts,replace_arg,remove_arg
OUT=Path(__file__).resolve().parent/'run-state-L68';OUT.mkdir(parents=True,exist_ok=False)
CFG=json.loads((Path(__file__).resolve().parent/'config.json').read_text())
args=list(CFG['args'])
for key in ('--mtp','--mtp-max-t'):remove_arg(args,key)
replace_arg(args,'--spec','2');replace_arg(args,'--max-context','1024');replace_arg(args,'--expert-cache','1500');replace_arg(args,'--prompt-cache','6')
remove_arg(args,'--adapt-every');remove_arg(args,'--adapt-accepted-only')
prompts=prepared_prompts(CFG,2);base=child_env(CFG);base['STRATA_PREFILL_CPU_SHARE']='0'
def env(name,batch):
 e=dict(base);e['STRATA_PREFILL_CPU_SHARE']='0'
 if batch:e.update({'STRATA_BATCH_GDN_DUMP_AT':'68','STRATA_BATCH_GDN_DUMP_PATH':str((OUT/(name+'-batch-gdn')).resolve())})
 else:e.update({'STRATA_STATE_HASH':'1','STRATA_ACCEPTED_PREFIX_TRACE':'1','STRATA_STATE_DUMP_GDN_AT':'68','STRATA_STATE_DUMP_GDN':str((OUT/(name+'-serial-gdn.bin')).resolve())})
 return e
def gen(engine,prompt,maxnew=96):
 return [x for x in engine.generate(prompt,maxnew,{'temperature':0},threading.Event()) if x is not None]
def serial(key):
 n='prompt0' if key=='slot-0' else 'prompt1';e=StrataEngine(CFG['exe'],args,cwd=CFG.get('cwd'),log=str(OUT/(n+'.log')),env=env(n,False))
 try:return gen(e,prompts[key])
 finally:e.close()
def batched():
 e=StrataEngine(CFG['exe'],args+['--batch','2'],cwd=CFG.get('cwd'),log=str(OUT/'batch.log'),env=env('batch',True))
 try:
  if e.batch!=2:raise RuntimeError(f'admitted {e.batch} slots')
  with ThreadPoolExecutor(max_workers=2) as pool:
   f=[pool.submit(gen,e,prompts[k]) for k in prompts];return [x.result() for x in f]
 finally:e.close()
out={'serial_prompt0':serial('slot-0'),'serial_prompt1':serial('slot-1'),'batch':batched()}
(OUT/'result.json').write_text(json.dumps({'state_length':68,'prompts':prompts,'output_prefixes':out},indent=2)+'\n')
print(json.dumps({'prompt0':len(out['serial_prompt0']),'prompt1':len(out['serial_prompt1']),'batch':[len(x) for x in out['batch']]}))
