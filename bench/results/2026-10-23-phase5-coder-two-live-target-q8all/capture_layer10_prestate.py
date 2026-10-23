#!/usr/bin/env python3
"""Capture layer-10 committed state after position 132 before the changed row."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from serve.server import StrataEngine,child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts,remove_arg,replace_arg

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
opts=p.parse_args();out=opts.output.resolve();out.mkdir(parents=True,exist_ok=False)
base=Path(__file__).resolve().parent
cfg=json.loads((base.parent/'2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json').read_text())
args=list(cfg['args'])
for key in ('--mtp','--mtp-max-t','--adapt-every','--adapt-accepted-only'):remove_arg(args,key)
replace_arg(args,'--spec','2');replace_arg(args,'--max-context','1024');replace_arg(args,'--expert-cache','1500');replace_arg(args,'--prompt-cache','6')
prompts=prepared_prompts(cfg,2)

def env_for(name):
 e=child_env(cfg);e.update({'STRATA_NATIVE_CPU_Q8_1_DOT':'all','STRATA_IQ_MT_MIN':'1','STRATA_PREFILL_CPU_SHARE':'0',
  'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER':'10','STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS':'132',
  'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH':str((out/f'{name}.stgcmt').resolve())});return e

def generate(engine,key):
 return [int(t) for t in engine.generate(prompts[key],96,{'temperature':0},threading.Event()) if t is not None]

serial=StrataEngine(cfg['exe'],args,cwd=cfg.get('cwd'),log=str(out/'serial-slot-1.log'),env=env_for('serial'))
try: serial_tokens=generate(serial,'slot-1')
finally: serial.close()
batch=StrataEngine(cfg['exe'],args+['--batch','2'],cwd=cfg.get('cwd'),log=str(out/'batch.log'),env=env_for('batch'))
try:
 if batch.batch!=2:raise RuntimeError(f'expected two batch slots, got {batch.batch}')
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={key:pool.submit(generate,batch,key) for key in prompts};batch_tokens={key:future.result() for key,future in futures.items()}
finally: batch.close()
result={'layer':10,'captured_position':132,'next_position':133,'serial_slot_1':serial_tokens,
        'batch':batch_tokens,'profile':{'live_requests':2,'mtp':False,'STRATA_NATIVE_CPU_Q8_1_DOT':'all','STRATA_IQ_MT_MIN':'1'}}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'position':132,'serial_tokens':len(serial_tokens),'batch_tokens':{k:len(v) for k,v in batch_tokens.items()}}))
