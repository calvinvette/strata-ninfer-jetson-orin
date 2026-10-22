#!/usr/bin/env python3
"""Compare all-layer committed GDN state at the first MTP2 batch mismatch."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path,
                    default=Path(__file__).resolve().parent / 'run-mtp2-first-state-drift-batch1-controls')
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
base_env = child_env(CFG)
base_env['STRATA_PREFILL_CPU_SHARE'] = '0'
positions = '67,74,76'


def make_env(name):
    env = dict(base_env)
    env.update({'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': 'all',
                'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': positions,
                'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((OUT / (name + '.stgcmt')).resolve()),
                'STRATA_PREFILL_CPU_SHARE': '0'})
    return env


def generate(engine, prompt):
    tokens = [token for token in engine.generate(prompt, 64, {'temperature': 0}, threading.Event())
              if token is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}


def serial(key):
    name = 'single-live-batch-mtp2-' + key
    engine = StrataEngine(CFG['exe'], args + ['--batch', '2', '--batch-mtp'], cwd=CFG.get('cwd'), log=str(OUT / (name + '.log')),
                          env=make_env(name))
    try:
        if engine.batch != 2:
            raise RuntimeError(f'{name}: expected two available batch slots, got {engine.batch}')
        return generate(engine, prompts[key])
    finally:
        engine.close()


def batch():
    name = 'batch-mtp2'
    engine = StrataEngine(CFG['exe'], args + ['--batch', '2', '--batch-mtp'], cwd=CFG.get('cwd'),
                          log=str(OUT / (name + '.log')), env=make_env(name))
    try:
        if engine.batch != 2:
            raise RuntimeError(f'only admitted {engine.batch} slots')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(generate, engine, prompts[key]) for key in prompts]
            return {key: future.result() for key, future in zip(prompts, futures)}
    finally:
        engine.close()


outputs = {'single_live_batch_mtp2': {key: serial(key) for key in prompts}, 'batch_mtp2': batch()}
(OUT / 'result.json').write_text(json.dumps({'state_positions': [67, 74, 76], 'prompts': prompts,
                                             'outputs': outputs}, indent=2) + '\n')
print(json.dumps({arm: {key: len(value['tokens']) for key, value in records.items()}
                  for arm, records in outputs.items()}))
