#!/usr/bin/env python3
"""Pair the first changed GDN state with the preceding layer-4 MoE row."""
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
parser.add_argument('--position', type=int, default=68)
parser.add_argument('--tokens', type=int, default=6)
parser.add_argument('--moe-layer', type=int, default=4)
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
cfg = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
engine_args = list(cfg['args'])
for key in ('--mtp', '--mtp-max-t', '--adapt-every', '--adapt-accepted-only'):
    remove_arg(engine_args, key)
replace_arg(engine_args, '--spec', '2')
replace_arg(engine_args, '--max-context', '1024')
replace_arg(engine_args, '--expert-cache', '1500')
replace_arg(engine_args, '--prompt-cache', '6')
prompts = prepared_prompts(cfg, 2)
base_env = child_env(cfg)

def make_env(stem, batch):
    env = dict(base_env)
    env.update({
        'STRATA_PREFILL_CPU_SHARE': '0',
        'STRATA_STATE_HASH': '1',
        'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': 'all',
        'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': str(args.position),
        'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out / f'{stem}.stgcmt').resolve()),
        'STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER': str(args.moe_layer),
        'STRATA_VERIFY_DUMP_MOE_ROUTE_POSITIONS': str(args.position),
        'STRATA_VERIFY_DUMP_MOE_ROUTE_BATCH': '1',
        'STRATA_VERIFY_DUMP_MOE_ROUTE_PATH': str((out / f'{stem}.routes.jsonl').resolve()),
        'STRATA_VERIFY_DUMP_MOE_PARTS_LAYER': str(args.moe_layer),
        'STRATA_VERIFY_DUMP_MOE_PARTS_POSITIONS': str(args.position),
        'STRATA_VERIFY_DUMP_MOE_PARTS_BATCH': '1',
        'STRATA_VERIFY_DUMP_MOE_PARTS_PATH': str((out / f'{stem}.parts.stmparts').resolve()),
        'STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER': str(args.moe_layer),
        'STRATA_VERIFY_DUMP_MOE_OUTPUT_POSITIONS': str(args.position),
        'STRATA_VERIFY_DUMP_MOE_OUTPUT_BATCH': '1',
        'STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH': str((out / f'{stem}.output.stmoe').resolve()),
        'STRATA_CAPTURE_MOE_PATH': str((out / f'{stem}.owners.jsonl').resolve()),
        'STRATA_CAPTURE_MOE_LAYER': str(args.moe_layer),
        'STRATA_CAPTURE_MOE_POSITIONS': str(args.position),
        'STRATA_CAPTURE_MOE_ROWS': '64',
    })
    if batch:
        env.update({'STRATA_INTEGRATION_TRACE': '1'})
    return env

def generate(engine, prompt):
    tokens = [int(t) for t in engine.generate(prompt, args.tokens, {'temperature': 0}, threading.Event())
              if t is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial = {}
for key, prompt in prompts.items():
    stem = 'serial-prompt0' if key == 'slot-0' else 'serial-prompt1'
    engine = StrataEngine(cfg['exe'], engine_args, cwd=cfg.get('cwd'),
                          log=str(out / f'{stem}.log'), env=make_env(stem, False))
    try:
        serial[key] = generate(engine, prompt)
    finally:
        engine.close()

engine = StrataEngine(cfg['exe'], engine_args + ['--batch', '2'], cwd=cfg.get('cwd'),
                      log=str(out / 'batch.log'), env=make_env('batch', True))
try:
    if engine.batch != 2:
        raise RuntimeError(f'expected two slots, admitted {engine.batch}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {key: pool.submit(generate, engine, prompt) for key, prompt in prompts.items()}
        batch = {key: futures[key].result() for key in prompts}
finally:
    engine.close()

result = {'layer': args.moe_layer, 'moe_position': args.position, 'state_position': args.position,
          'profile': {'live_requests': 2, 'batch_slots': 2, 'mtp': False,
                      'context': 1024, 'expert_cache_mib': 1500},
          'prompts': prompts, 'serial': serial, 'batch': batch,
          'token_match': {key: serial[key]['tokens'] == batch[key]['tokens'] for key in prompts}}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'token_match': result['token_match'],
                  'batch_lengths': {k: len(v['tokens']) for k, v in batch.items()}}))
