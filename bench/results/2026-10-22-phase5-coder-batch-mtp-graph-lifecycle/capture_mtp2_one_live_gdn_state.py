#!/usr/bin/env python3
"""Capture all-layer GDN commits for a one-live-after-admission MTP2 batch slot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--position', type=int, default=None, help='single commit position (legacy form)')
p.add_argument('--positions', help='comma-separated commit positions')
p.add_argument('--admit-after-tokens', type=int, default=1,
               help='submit the one-token competitor after this many slot-0 outputs')
p.add_argument('--mode', choices=('mtp2', 'target-only'), default='mtp2')
args = p.parse_args()
if args.position is not None and args.positions is not None:
    p.error('use --position or --positions, not both')
positions = ([args.position] if args.position is not None else
             [int(x) for x in args.positions.split(',')] if args.positions else [126])
if not positions or positions != sorted(set(positions)) or positions[0] < 0:
    p.error('commit positions must be sorted, unique and non-negative')
if args.admit_after_tokens < 1:
    p.error('--admit-after-tokens must be positive')
os.environ['STRATA_PARALLEL_SOLO'] = '0'
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
cfg = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
engine_args = list(cfg['args'])
if args.mode == 'target-only':
    remove_arg(engine_args, '--mtp')
    remove_arg(engine_args, '--mtp-max-t')
replace_arg(engine_args, '--spec', '2')
replace_arg(engine_args, '--max-context', '1024')
replace_arg(engine_args, '--expert-cache', '1500')
replace_arg(engine_args, '--prompt-cache', '6')
remove_arg(engine_args, '--adapt-every')
remove_arg(engine_args, '--adapt-accepted-only')
prompts = prepared_prompts(cfg, 2)

def make_env(name):
    env = child_env(cfg)
    env.update({'STRATA_PREFILL_CPU_SHARE': '0',
                'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': 'all',
                'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': ','.join(map(str, positions)),
                'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out / f'{name}.stgcmt').resolve())})
    return env

def generate(engine, key, limit, ready=None):
    tokens = []
    for token in engine.generate(prompts[key], limit, {'temperature': 0}, threading.Event()):
        if token is not None:
            tokens.append(token)
            if ready is not None and key == 'slot-0' and len(tokens) >= args.admit_after_tokens:
                ready.set()
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial_engine = StrataEngine(cfg['exe'], engine_args, cwd=cfg.get('cwd'), log=str(out / 'serial.log'), env=make_env('serial'))
try:
    serial = generate(serial_engine, 'slot-0', 96)
finally:
    serial_engine.close()
batch_args = engine_args + ['--batch', '2']
if args.mode == 'mtp2':
    batch_args.append('--batch-mtp')
batch_engine = StrataEngine(cfg['exe'], batch_args, cwd=cfg.get('cwd'),
                            log=str(out / 'batch.log'), env=make_env('batch'))
try:
    if batch_engine.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {batch_engine.batch}')
    first = threading.Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(generate, batch_engine, 'slot-0', 96, first)
        if not first.wait(timeout=300):
            raise TimeoutError(f'slot 0 did not emit {args.admit_after_tokens} tokens before competitor admission')
        b = pool.submit(generate, batch_engine, 'slot-1', 1)
        batch = {'slot-0': a.result(), 'slot-1': b.result()}
finally:
    batch_engine.close()
result = {'mode': args.mode, 'positions': positions,
          'admit_after_tokens': args.admit_after_tokens, 'prompts': prompts,
          'outputs': {'serial-slot-0': serial, 'batch': batch}}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'serial_tokens': len(serial['tokens']),
                  'batch_tokens': {k: len(v['tokens']) for k, v in batch.items()},
                  'slot_0_exact': serial['tokens'] == batch['slot-0']['tokens']}))
