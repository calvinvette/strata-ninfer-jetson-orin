#!/usr/bin/env python3
"""Check the default batch-MTP graph cap and short single-request output."""
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-default-graph-cap'
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
env.pop('STRATA_BATCH_MTP_GRAPH_LIMIT', None)
env['STRATA_PREFILL_CPU_SHARE'] = '0'

def generate(engine):
    return [token for token in engine.generate(prompt, 6, {'temperature': 0}, threading.Event())
            if token is not None]

serial = StrataEngine(CFG['exe'], args, cwd=CFG.get('cwd'), log=str(OUT / 'serial-mtp2.log'), env=env)
try:
    serial_tokens = generate(serial)
finally:
    serial.close()
batch = StrataEngine(CFG['exe'], args + ['--batch', '2', '--batch-mtp'], cwd=CFG.get('cwd'),
                     log=str(OUT / 'batch-mtp.log'), env=env)
try:
    if batch.batch != 2:
        raise RuntimeError(f'only admitted {batch.batch} batch slots')
    batch_tokens = generate(batch)
finally:
    batch.close()
result = {'profile': {'batch_slots': 2, 'mtp_depth': 2, 'max_new': 6,
                      'graph_pool_limit_override': None, 'expected_default_graph_pool_limit': 64},
          'serial_tokens': serial_tokens, 'batch_tokens': batch_tokens,
          'outputs_match': serial_tokens == batch_tokens}
(OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'profile': result['profile'], 'outputs_match': result['outputs_match'],
                  'tokens': len(batch_tokens)}))
if not result['outputs_match']:
    raise SystemExit(2)
