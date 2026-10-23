#!/usr/bin/env python3
"""Check two-slot target-only batch with STRATA_IQ_MT_MIN=1."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-two-active-target-slots-mtmin1'
OUT.mkdir(parents=True, exist_ok=False)
CFG = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
args = list(CFG['args'])
for key in ('--mtp', '--mtp-max-t'):
    remove_arg(args, key)
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', '1500')
replace_arg(args, '--prompt-cache', '6')
remove_arg(args, '--adapt-every')
remove_arg(args, '--adapt-accepted-only')
prompts = prepared_prompts(CFG, 2)
env = child_env(CFG)
env.update({'STRATA_IQ_MT_MIN':'1','STRATA_INTEGRATION_TRACE':'1','STRATA_STATE_HASH':'1','STRATA_PREFILL_CPU_SHARE':'0'})

def generate(engine, prompt):
    toks = [x for x in engine.generate(prompt, 96, {'temperature': 0}, threading.Event()) if x is not None]
    return {'tokens': toks, 'finish': engine.last.get('finish')}

serial = StrataEngine(CFG['exe'], args, cwd=CFG.get('cwd'), log=str(OUT/'serial-target-only.log'), env=env)
try:
    serial_outputs = {name: generate(serial, prompts[name]) for name in prompts}
finally:
    serial.close()
batch = StrataEngine(CFG['exe'], args+['--batch','2'], cwd=CFG.get('cwd'), log=str(OUT/'batch-target-only.log'), env=env)
try:
    if batch.batch != 2: raise RuntimeError(f'only admitted {batch.batch} batch slots')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(generate,batch,prompts[name]) for name in prompts}
        batch_outputs = {name:futures[name].result() for name in prompts}
finally:
    batch.close()
match={name:serial_outputs[name]['tokens']==batch_outputs[name]['tokens'] for name in prompts}
first={name:next((i for i,(a,b) in enumerate(zip(serial_outputs[name]['tokens'],batch_outputs[name]['tokens'])) if a!=b),None) for name in prompts}
result={'profile':{'live_requests':2,'batch_slots':2,'mtp':False,'context':1024,'expert_cache_mib':1500,'STRATA_IQ_MT_MIN':1},'prompts':prompts,'serial_target_only':serial_outputs,'batch_target_only':batch_outputs,'per_prompt_match':match,'first_mismatch_index':first,'all_outputs_match':all(match.values())}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('profile','per_prompt_match','first_mismatch_index')}))
if not result['all_outputs_match']: raise SystemExit(2)
