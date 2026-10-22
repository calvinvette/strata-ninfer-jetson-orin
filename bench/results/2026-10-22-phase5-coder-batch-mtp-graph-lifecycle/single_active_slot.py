#!/usr/bin/env python3
"""Compare one live --batch-mtp request with serial MTP2 on identical settings."""
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-single-active-slot'
OUT.mkdir(parents=True, exist_ok=False)
CFG = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
args = list(CFG['args'])
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', '1500')
replace_arg(args, '--prompt-cache', '6')
remove_arg(args, '--adapt-every')
remove_arg(args, '--adapt-accepted-only')
prompt = prepared_prompts(CFG, 2)['slot-1']
env = child_env(CFG)
env.update({'STRATA_INTEGRATION_TRACE':'1','STRATA_STATE_HASH':'1','STRATA_PREFILL_CPU_SHARE':'0'})

def generate(engine):
    toks = [x for x in engine.generate(prompt, 96, {'temperature': 0}, threading.Event()) if x is not None]
    return {'tokens': toks, 'finish': engine.last.get('finish')}

serial = StrataEngine(CFG['exe'], args, cwd=CFG.get('cwd'), log=str(OUT/'serial-mtp2.log'), env=env)
try:
    serial_output = generate(serial)
finally:
    serial.close()
batch_args = args + ['--batch','8','--batch-mtp']
batch = StrataEngine(CFG['exe'], batch_args, cwd=CFG.get('cwd'), log=str(OUT/'batch-mtp.log'), env=env)
try:
    if batch.batch != 8:
        raise RuntimeError(f'only admitted {batch.batch} batch slots')
    batch_output = generate(batch)
finally:
    batch.close()
result = {'prompt':prompt,'profile':{'live_requests':1,'batch_slots':8,'mtp_depth':2,'context':1024,'expert_cache_mib':1500},
          'serial_mtp2':serial_output,'single_active_batch_mtp':batch_output,
          'outputs_match':serial_output['tokens']==batch_output['tokens'],
          'first_mismatch_index':next((i for i,(a,b) in enumerate(zip(serial_output['tokens'],batch_output['tokens'])) if a!=b),None)}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('profile','outputs_match','first_mismatch_index')}))
if not result['outputs_match']:
    raise SystemExit(2)
