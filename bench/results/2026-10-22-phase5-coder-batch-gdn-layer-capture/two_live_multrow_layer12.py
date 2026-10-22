#!/usr/bin/env python3
"""Capture layer 12 around the known two-live target-only mismatch."""
from concurrent.futures import ThreadPoolExecutor
import argparse
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
parser.add_argument('--layer', type=int, default=12)
parser.add_argument('--positions', default=','.join(map(str, range(120, 133))))
parser.add_argument('--commit-layer', default='-1',
                    help='also capture committed recurrent state at a GDN layer, or all')
parser.add_argument('--max-new', type=int, default=96)
parser.add_argument('--moe-output-layer', type=int, default=-1,
                    help='also capture shared and combined MoE outputs at this layer')
args = parser.parse_args()
positions = [int(value) for value in args.positions.split(',')]
if positions != sorted(set(positions)) or not positions or positions[0] < 0:
    parser.error('--positions must be sorted unique non-negative integers')
if args.layer < 0:
    parser.error('--layer must be non-negative')
if args.moe_output_layer < -1:
    parser.error('--moe-output-layer must be -1 or non-negative')
if args.commit_layer != 'all':
    try:
        args.commit_layer = int(args.commit_layer)
    except ValueError:
        parser.error('--commit-layer must be -1, all, or a non-negative GDN layer')
    if args.commit_layer < -1:
        parser.error('--commit-layer must be -1, all, or a non-negative GDN layer')
if args.max_new < 1:
    parser.error('--max-new must be positive')

out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
case_dir = Path(__file__).resolve().parents[1] / '2026-10-22-phase5-coder-batch-mtp-graph-lifecycle'
cfg = json.loads((case_dir / 'config.json').read_text())
engine_args = list(cfg['args'])
for key in ('--mtp', '--mtp-max-t', '--adapt-every', '--adapt-accepted-only'):
    remove_arg(engine_args, key)
replace_arg(engine_args, '--spec', '2')
replace_arg(engine_args, '--max-context', '1024')
replace_arg(engine_args, '--expert-cache', '1500')
replace_arg(engine_args, '--prompt-cache', '6')
prompts = prepared_prompts(cfg, 2)

def make_env(name):
    env = child_env(cfg)
    env.update({'STRATA_PREFILL_CPU_SHARE': '0',
                'STRATA_VERIFY_DUMP_GDN_LAYER': str(args.layer),
                'STRATA_VERIFY_DUMP_GDN_POSITIONS': ','.join(map(str, positions)),
                'STRATA_VERIFY_DUMP_GDN_BATCH': '1',
                'STRATA_VERIFY_DUMP_GDN_PATH': str((out / f'{name}.stgdiag').resolve())})
    if args.moe_output_layer >= 0:
        env.update({'STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER': str(args.moe_output_layer),
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_POSITIONS': ','.join(map(str, positions)),
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_BATCH': '1',
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH': str((out / f'{name}.stmoe').resolve())})
    if args.commit_layer != -1:
        env.update({'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': str(args.commit_layer),
                    'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': ','.join(map(str, positions)),
                    'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out / f'{name}.stgcmt').resolve())})
    return env

def generate(engine, prompt):
    tokens = [token for token in engine.generate(prompt, args.max_new, {'temperature': 0}, threading.Event())
              if token is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial = {}
for name in ('slot-0', 'slot-1'):
    engine = StrataEngine(cfg['exe'], engine_args, cwd=cfg.get('cwd'),
                          log=str(out / f'serial-{name}.log'), env=make_env(f'serial-{name}'))
    try:
        serial[name] = generate(engine, prompts[name])
    finally:
        engine.close()

batch_engine = StrataEngine(cfg['exe'], engine_args + ['--batch', '2'], cwd=cfg.get('cwd'),
                            log=str(out / 'batch.log'), env=make_env('batch'))
try:
    if batch_engine.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {batch_engine.batch}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(generate, batch_engine, prompts[name]) for name in prompts}
        batch = {name: futures[name].result() for name in prompts}
finally:
    batch_engine.close()

first_mismatch = {}
for name in ('slot-0', 'slot-1'):
    first_mismatch[name] = next((i for i, (a, b) in
                                 enumerate(zip(serial[name]['tokens'], batch[name]['tokens'])) if a != b), None)
result = {'model': cfg['model_name'], 'mode': 'two-live-target-only', 'layer': args.layer,
          'positions': positions, 'max_new': args.max_new, 'commit_layer': args.commit_layer,
          'moe_output_layer': args.moe_output_layer,
          'prompts': prompts, 'serial_fresh': serial, 'batch': batch,
          'first_mismatch_index': first_mismatch}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'serial_tokens': {k: len(v['tokens']) for k, v in serial.items()},
                  'batch_tokens': {k: len(v['tokens']) for k, v in batch.items()},
                  'first_mismatch_index': first_mismatch}))
