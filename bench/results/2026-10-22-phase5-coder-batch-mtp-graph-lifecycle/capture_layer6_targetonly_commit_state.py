#!/usr/bin/env python3
"""Capture target-only model-layer-6 committed GDN state around first batch drift."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-layer6-targetonly-commit-state'
OUT.mkdir(parents=True, exist_ok=False)
CFG = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
args = list(CFG['args'])
remove_arg(args, '--mtp')
remove_arg(args, '--mtp-max-t')
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', '1500')
replace_arg(args, '--prompt-cache', '6')
remove_arg(args, '--adapt-every')
remove_arg(args, '--adapt-accepted-only')
prompts = prepared_prompts(CFG, 2)
positions = '67,68,69,70,71,72'
base_env = child_env(CFG)
base_env['STRATA_PREFILL_CPU_SHARE'] = '0'


def make_env(name):
    env = dict(base_env)
    env.update({'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': '6',
                'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': positions,
                'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((OUT / (name + '.stgcmt')).resolve()),
                'STRATA_PREFILL_CPU_SHARE': '0'})
    return env


def generate(engine, prompt):
    return [token for token in engine.generate(prompt, 6, {'temperature': 0}, threading.Event())
            if token is not None]


def serial(key):
    name = 'serial-' + key
    engine = StrataEngine(CFG['exe'], args, cwd=CFG.get('cwd'), log=str(OUT / (name + '.log')),
                          env=make_env(name))
    try:
        return generate(engine, prompts[key])
    finally:
        engine.close()


def batch():
    name = 'batch'
    engine = StrataEngine(CFG['exe'], args + ['--batch', '2'], cwd=CFG.get('cwd'),
                          log=str(OUT / (name + '.log')), env=make_env(name))
    try:
        if engine.batch != 2:
            raise RuntimeError(f'only admitted {engine.batch} slots')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(generate, engine, prompts[key]) for key in prompts]
            return {key: future.result() for key, future in zip(prompts, futures)}
    finally:
        engine.close()


outputs = {'serial': {key: serial(key) for key in prompts}, 'batch': batch()}
(OUT / 'result.json').write_text(json.dumps({'model_layer': 6, 'selected_commit_positions': [67, 68, 69, 70, 71, 72],
                                             'prompts': prompts, 'outputs': outputs}, indent=2) + '\n')
print(json.dumps({arm: {key: len(tokens) for key, tokens in values.items()}
                  for arm, values in outputs.items()}))
