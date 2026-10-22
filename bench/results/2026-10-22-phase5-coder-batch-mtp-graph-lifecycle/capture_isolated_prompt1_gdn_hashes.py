#!/usr/bin/env python3
"""Capture standalone per-layer GDN accepted-prefix hashes for prompt 1."""
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-isolated-prompt1-gdn'
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
results = {}

for name, mtp in [('target-only', False), ('mtp2', True)]:
    arm = list(args)
    if not mtp:
        remove_arg(arm, '--mtp')
        remove_arg(arm, '--mtp-max-t')
    env = child_env(CFG)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                'STRATA_STATE_HASH_GDN': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    engine = StrataEngine(CFG['exe'], arm, cwd=CFG.get('cwd'),
                          log=str(OUT / (name + '.log')), env=env)
    try:
        results[name] = [token for token in engine.generate(prompt, 96, {'temperature': 0}, threading.Event())
                         if token is not None]
    finally:
        engine.close()

(OUT / 'result.json').write_text(json.dumps({'prompt': prompt, 'outputs': results}, indent=2) + '\n')
print(json.dumps({name: len(tokens) for name, tokens in results.items()}))
