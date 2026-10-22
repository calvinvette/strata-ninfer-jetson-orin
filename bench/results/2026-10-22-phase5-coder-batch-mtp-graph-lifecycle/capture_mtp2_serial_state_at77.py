#!/usr/bin/env python3
"""Capture serial MTP2 GDN state after processing committed input position 76."""
import argparse
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
OUT = parser.parse_args().output.resolve()
OUT.mkdir(parents=True, exist_ok=False)
CFG = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
args = list(CFG['args'])
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', '1500')
replace_arg(args, '--prompt-cache', '6')
remove_arg(args, '--adapt-every')
remove_arg(args, '--adapt-accepted-only')
prompts = prepared_prompts(CFG, 2)
results = {}
for key in ('slot-0', 'slot-1'):
    name = 'serial-' + key
    env = child_env(CFG)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_PREFILL_CPU_SHARE': '0',
                'STRATA_STATE_DUMP_GDN_AT': '77',
                'STRATA_STATE_DUMP_GDN': str((OUT / (name + '.gdn')).resolve())})
    engine = StrataEngine(CFG['exe'], args, cwd=CFG.get('cwd'), log=str(OUT / (name + '.log')), env=env)
    try:
        tokens = [x for x in engine.generate(prompts[key], 10, {'temperature': 0}, threading.Event()) if x is not None]
        results[key] = {'tokens': tokens, 'finish': engine.last.get('finish')}
    finally:
        engine.close()
(OUT / 'result.json').write_text(json.dumps({'state_length': 77, 'input_position': 76,
                                             'prompts': prompts, 'outputs': results}, indent=2) + '\n')
print(json.dumps({key: len(value['tokens']) for key, value in results.items()}))
