#!/usr/bin/env python3
"""Capture target-only GDN layer inputs/outputs around delayed batch drift."""
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

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--layer', type=int, default=12)
parser.add_argument('--positions', default='118,119,120')
parser.add_argument('--admit-after-tokens', type=int, default=48)
args = parser.parse_args()
positions = [int(value) for value in args.positions.split(',')]
if positions != sorted(set(positions)) or not positions or positions[0] < 0:
    parser.error('--positions must be sorted unique non-negative integers')
if args.layer < 0 or args.admit_after_tokens < 1:
    parser.error('--layer must be non-negative and admission count positive')

out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
cfg = json.loads((Path(__file__).resolve().parents[1] /
                  '2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json').read_text())
engine_args = list(cfg['args'])
remove_arg(engine_args, '--mtp')
remove_arg(engine_args, '--mtp-max-t')
replace_arg(engine_args, '--max-context', '1024')
replace_arg(engine_args, '--expert-cache', '1500')
replace_arg(engine_args, '--prompt-cache', '6')
remove_arg(engine_args, '--adapt-every')
remove_arg(engine_args, '--adapt-accepted-only')
prompts = prepared_prompts(cfg, 2)

def make_env(name):
    env = child_env(cfg)
    capture_positions = positions
    env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_PARALLEL_SOLO': '0',
                'STRATA_VERIFY_DUMP_GDN_LAYER': str(args.layer),
                'STRATA_VERIFY_DUMP_GDN_POSITIONS': ','.join(map(str, capture_positions)),
                'STRATA_VERIFY_DUMP_GDN_BATCH': '1',
                'STRATA_VERIFY_DUMP_GDN_PATH': str((out / f'{name}.stgdiag').resolve())})
    return env

def generate(engine, key, limit, ready=None):
    tokens = []
    for token in engine.generate(prompts[key], limit, {'temperature': 0}, threading.Event()):
        if token is not None:
            tokens.append(token)
            if ready is not None and key == 'slot-0' and len(tokens) >= args.admit_after_tokens:
                ready.set()
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial_engine = StrataEngine(cfg['exe'], engine_args, cwd=cfg.get('cwd'),
                             log=str(out / 'serial.log'), env=make_env('serial'))
try:
    serial = generate(serial_engine, 'slot-0', 96)
finally:
    serial_engine.close()

batch_engine = StrataEngine(cfg['exe'], engine_args + ['--batch', '2'], cwd=cfg.get('cwd'),
                            log=str(out / 'batch.log'), env=make_env('batch'))
try:
    if batch_engine.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {batch_engine.batch}')
    admitted = threading.Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        long_request = pool.submit(generate, batch_engine, 'slot-0', 96, admitted)
        if not admitted.wait(timeout=300):
            raise TimeoutError('slot 0 did not emit the delayed-admission prefix')
        short_request = pool.submit(generate, batch_engine, 'slot-1', 1)
        batch = {'slot-0': long_request.result(), 'slot-1': short_request.result()}
finally:
    batch_engine.close()

result = {'model': cfg['model_name'], 'mode': 'target-only', 'layer': args.layer,
          'positions': positions, 'admit_after_tokens': args.admit_after_tokens,
          'prompts': prompts, 'outputs': {'serial': serial, 'batch': batch}}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'serial_tokens': len(serial['tokens']),
                  'batch_tokens': {key: len(value['tokens']) for key, value in batch.items()},
                  'slot_0_exact': serial['tokens'] == batch['slot-0']['tokens']}))
