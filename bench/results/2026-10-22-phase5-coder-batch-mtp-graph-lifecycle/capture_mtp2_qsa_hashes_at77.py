#!/usr/bin/env python3
"""Compare per-layer QSA/GDN hashes at MTP2 state length 77."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--serial-kv-appends', action='store_true',
                    help='disable batched K/V and indexer appends for the batch-MTP arm')
parser.add_argument('--per-token-verify', action='store_true',
                    help='disable decoder batched projections/updates for the batch-MTP arm')
parser.add_argument('--reverse-arrival', action='store_true',
                    help='start the batch requests in reverse prompt order with a 250 ms stagger')
parser.add_argument('--duplicate-prompt', action='store_true',
                    help='run prompt slot-0 in both requests to check batch row state isolation')
ARGS = parser.parse_args()
SERIAL_KV_APPENDS = ARGS.serial_kv_appends
PER_TOKEN_VERIFY = ARGS.per_token_verify
REVERSE_ARRIVAL = ARGS.reverse_arrival
DUPE_PROMPT = ARGS.duplicate_prompt
OUT = ARGS.output.resolve()
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
if DUPE_PROMPT:
    prompts = {'slot-0': prompts['slot-0'], 'slot-1': prompts['slot-0']}


def arm(name, arm_args, env, requests):
    engine = StrataEngine(CFG['exe'], arm_args, cwd=CFG.get('cwd'), log=str(OUT / (name + '.log')), env=env)
    try:
        if '--batch' in arm_args and engine.batch != 2:
            raise RuntimeError(f'{name}: expected two batch slots, got {engine.batch}')
        def generate(key):
            tokens = [x for x in engine.generate(prompts[key], 10, {'temperature': 0}, threading.Event())
                      if x is not None]
            return {'tokens': tokens, 'finish': engine.last.get('finish')}
        if len(requests) == 1:
            return {requests[0]: generate(requests[0])}
        with ThreadPoolExecutor(max_workers=len(requests)) as pool:
            order = list(reversed(requests)) if REVERSE_ARRIVAL and name == 'batch' else list(requests)
            futures = {order[0]: pool.submit(generate, order[0])}
            if REVERSE_ARRIVAL and name == 'batch':
                time.sleep(0.25)
            futures[order[1]] = pool.submit(generate, order[1])
            return {key: future.result() for key, future in futures.items()}
    finally:
        engine.close()


def make_env(name):
    env = child_env(CFG)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                'STRATA_STATE_HASH_QSA_LAYERS': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                'STRATA_PREFILL_CPU_SHARE': '0'})
    if name == 'batch':
        env.update({'STRATA_BATCH_QSA_HASH_PATH': str(OUT / 'batch-qsa-state-hashes.txt'),
                    'STRATA_BATCH_QSA_HASH_FROM': '67', 'STRATA_BATCH_QSA_HASH_TO': '76'})
        if SERIAL_KV_APPENDS:
            env['STRATA_NO_BATCH_KV_STEP'] = '1'
        if PER_TOKEN_VERIFY:
            env['STRATA_DEC_BATCH'] = '0'
    return env


serial = {key: arm('serial-' + key, args, make_env(key), [key])[key] for key in prompts}
batch = arm('batch-mtp2', args + ['--batch', '2', '--batch-mtp'], make_env('batch'), list(prompts))
(OUT / 'result.json').write_text(json.dumps({
    'state_length': 77,
    'batch_append_mode': 'per-token' if SERIAL_KV_APPENDS else 'batched',
    'decoder_compute_mode': 'per-token' if PER_TOKEN_VERIFY else 'batched',
    'arrival_order': 'reverse-with-250ms-stagger' if REVERSE_ARRIVAL else 'concurrent',
    'duplicate_prompt': DUPE_PROMPT,
    'outputs': {'serial': serial, 'batch': batch},
}, indent=2) + '\n')
print(json.dumps({arm_name: {key: len(value['tokens']) for key, value in rows.items()}
                  for arm_name, rows in {'serial': serial, 'batch': batch}.items()}))
