#!/usr/bin/env python3
"""Compare two identical live prompts in the MTP2 batch path."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
prompt = prepared_prompts(CFG, 2)['slot-0']
prompts = {'duplicate-a': prompt, 'duplicate-b': prompt}
env = child_env(CFG)
env.update({'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': 'all',
            'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': '67,74,76',
            'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((OUT / 'identical-prompts.stgcmt').resolve()),
            'STRATA_BATCH_QSA_HASH_PATH': str((OUT / 'batch-qsa-state-hashes.txt').resolve()),
            'STRATA_BATCH_QSA_HASH_FROM': '67', 'STRATA_BATCH_QSA_HASH_TO': '76',
            'STRATA_PREFILL_CPU_SHARE': '0'})


def generate(engine, ids):
    tokens = [x for x in engine.generate(ids, 64, {'temperature': 0}, threading.Event()) if x is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}


engine = StrataEngine(CFG['exe'], args + ['--batch', '2', '--batch-mtp'], cwd=CFG.get('cwd'),
                      log=str(OUT / 'engine.log'), env=env)
try:
    if engine.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {engine.batch}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {key: pool.submit(generate, engine, ids) for key, ids in prompts.items()}
        outputs = {key: future.result() for key, future in futures.items()}
finally:
    engine.close()
(OUT / 'result.json').write_text(json.dumps({'positions': [67, 74, 76], 'prompts': prompts,
                                             'outputs': outputs}, indent=2) + '\n')
print(json.dumps({key: len(value['tokens']) for key, value in outputs.items()}))
