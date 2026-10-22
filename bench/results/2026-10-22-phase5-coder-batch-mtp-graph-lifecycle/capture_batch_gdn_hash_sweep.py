#!/usr/bin/env python3
"""Pair per-layer committed GDN hashes across serial and two-row decode positions."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-gdn-hash-sweep'
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
base_env = child_env(CFG)
base_env['STRATA_PREFILL_CPU_SHARE'] = '0'


def arm_args(mtp):
    result = list(args)
    if not mtp:
        remove_arg(result, '--mtp')
        remove_arg(result, '--mtp-max-t')
    return result


def generate(engine, prompt):
    tokens = [t for t in engine.generate(prompt, 96, {'temperature': 0}, threading.Event()) if t is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}


def serial(mtp):
    name = 'serial-mtp2' if mtp else 'serial-target-only'
    env = dict(base_env)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                'STRATA_STATE_HASH_GDN': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    engine = StrataEngine(CFG['exe'], arm_args(mtp), cwd=CFG.get('cwd'),
                          log=str(OUT / (name + '.log')), env=env)
    try:
        return {key: generate(engine, prompts[key]) for key in prompts}
    finally:
        engine.close()


def batch(mtp):
    name = 'batch-mtp2' if mtp else 'batch-target-only'
    env = dict(base_env)
    env.update({'STRATA_BATCH_GDN_HASH_PATH': str((OUT / (name + '-gdn-hashes.txt')).resolve()),
                'STRATA_BATCH_GDN_HASH_FROM': '68', 'STRATA_BATCH_GDN_HASH_TO': '127',
                'STRATA_PREFILL_CPU_SHARE': '0'})
    cmd = arm_args(mtp) + ['--batch', '2']
    if mtp:
        cmd.append('--batch-mtp')
    engine = StrataEngine(CFG['exe'], cmd, cwd=CFG.get('cwd'), log=str(OUT / (name + '.log')), env=env)
    try:
        if engine.batch != 2:
            raise RuntimeError(f'{name}: only admitted {engine.batch} batch slots')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(generate, engine, prompts[key]) for key in prompts]
            outputs = [f.result() for f in futures]
        return {key: value for key, value in zip(prompts, outputs)}
    finally:
        engine.close()


result = {
    'model': 'Qwen3.8-Flash-Next-Coder-GGUF-IQ1_M',
    'batch_hash_positions_inclusive': [68, 127],
    'prompt_tokens': prompts,
    'arms': {},
    'notes': 'Serial logs emit accepted-prefix per-layer hashes. Batch logs contain pre-verifier committed state hashes keyed by position, slot and row. Match batch rows to serial prompts by the position-68 hashes; physical slot assignment may vary.',
}
for label, mtp in [('target-only', False), ('mtp2', True)]:
    result['arms'][label] = {'serial': serial(mtp), 'batch': batch(mtp)}
(OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({name: {path: {key: len(val['tokens']) for key, val in arm[path].items()}
                              for path in ('serial', 'batch')}
                   for name, arm in result['arms'].items()}))
