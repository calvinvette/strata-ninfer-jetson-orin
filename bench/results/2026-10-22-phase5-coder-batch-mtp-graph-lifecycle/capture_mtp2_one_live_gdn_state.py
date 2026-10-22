#!/usr/bin/env python3
"""Capture all-layer GDN commits for a one-live-after-admission MTP2 batch slot."""
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

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--position', type=int, default=126)
args = p.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
cfg = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
engine_args = list(cfg['args'])
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
                'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': str(args.position),
                'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out / f'{name}.stgcmt').resolve())})
    return env

def generate(engine, key, limit, first=None):
    tokens = []
    for token in engine.generate(prompts[key], limit, {'temperature': 0}, threading.Event()):
        if token is not None:
            tokens.append(token)
            if first is not None and key == 'slot-0':
                first.set()
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial_engine = StrataEngine(cfg['exe'], engine_args, cwd=cfg.get('cwd'), log=str(out / 'serial.log'), env=make_env('serial'))
try:
    serial = generate(serial_engine, 'slot-0', 96)
finally:
    serial_engine.close()
batch_engine = StrataEngine(cfg['exe'], engine_args + ['--batch', '2', '--batch-mtp'], cwd=cfg.get('cwd'),
                            log=str(out / 'batch.log'), env=make_env('batch'))
try:
    if batch_engine.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {batch_engine.batch}')
    first = threading.Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(generate, batch_engine, 'slot-0', 96, first)
        if not first.wait(timeout=120):
            raise TimeoutError('slot 0 did not emit a token before competitor admission')
        b = pool.submit(generate, batch_engine, 'slot-1', 1)
        batch = {'slot-0': a.result(), 'slot-1': b.result()}
finally:
    batch_engine.close()
result = {'position': args.position, 'prompts': prompts,
          'outputs': {'serial-slot-0': serial, 'batch': batch}}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'serial_tokens': len(serial['tokens']),
                  'batch_tokens': {k: len(v['tokens']) for k, v in batch.items()},
                  'slot_0_exact': serial['tokens'] == batch['slot-0']['tokens']}))
