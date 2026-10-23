#!/usr/bin/env python3
"""Capture the missing fresh serial slot-0 layer-10 row at position 133."""
import argparse
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, remove_arg, replace_arg

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
opts=p.parse_args();out=opts.output.resolve();out.mkdir(parents=True,exist_ok=False)
base=Path(__file__).resolve().parent
cfg=json.loads((base.parent/'2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json').read_text())
args=list(cfg['args'])
for key in ('--mtp','--mtp-max-t','--adapt-every','--adapt-accepted-only'):remove_arg(args,key)
replace_arg(args,'--spec','2');replace_arg(args,'--max-context','1024');replace_arg(args,'--expert-cache','1500');replace_arg(args,'--prompt-cache','6')
prompts=prepared_prompts(cfg,2)
env=child_env(cfg);env.update({'STRATA_NATIVE_CPU_Q8_1_DOT':'all','STRATA_IQ_MT_MIN':'1','STRATA_PREFILL_CPU_SHARE':'0',
 'STRATA_VERIFY_DUMP_GDN_LAYER':'10','STRATA_VERIFY_DUMP_GDN_PATH':str((out/'serial-slot-0.stgdiag').resolve()),
 'STRATA_VERIFY_DUMP_GDN_POSITIONS':'133','STRATA_VERIFY_DUMP_GDN_BATCH':'1'})
eng=StrataEngine(cfg['exe'],args,cwd=cfg.get('cwd'),log=str(out/'serial-slot-0.log'),env=env)
try:
 tokens=[int(t) for t in eng.generate(prompts['slot-0'],96,{'temperature':0},threading.Event()) if t is not None]
finally:eng.close()
(out/'result.json').write_text(json.dumps({'position':133,'layer':10,'tokens':tokens,'prompt_tokens':len(prompts['slot-0'])},indent=2)+'\n')
print(json.dumps({'prompt_tokens':len(prompts['slot-0']),'generated_tokens':len(tokens),'token_at_65':tokens[65]}))
