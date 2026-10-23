#!/usr/bin/env python3
"""Capture GDN stage arrays at the target-only delayed-batch divergence."""
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
parser.add_argument('--layer', type=int, default=12, help='zero-based model layer; must be a GDN layer')
parser.add_argument('--boundary-layer', type=int,
                    help='also capture the residual/GR-read boundary after this layer')
parser.add_argument('--moe-layer', type=int,
                    help='also capture batch-aware routing, expert parts, and MoE output at this layer')
parser.add_argument('--expert-cache-mib', type=int, default=1500)
parser.add_argument('--all-layer-commit-state', action='store_true',
                    help='also capture every committed GDN layer at position 119')
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
cfg = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
engine_args = list(cfg['args'])
for key in ('--mtp', '--mtp-max-t', '--adapt-every', '--adapt-accepted-only'):
    remove_arg(engine_args, key)
replace_arg(engine_args, '--spec', '2')
replace_arg(engine_args, '--max-context', '1024')
replace_arg(engine_args, '--expert-cache', str(args.expert_cache_mib))
replace_arg(engine_args, '--prompt-cache', '6')
prompts = prepared_prompts(cfg, 2)

def make_env(name):
    env = child_env(cfg)
    env.update({
        'STRATA_PREFILL_CPU_SHARE': '0',
        'STRATA_PARALLEL_SOLO': '0',
        'STRATA_VERIFY_DUMP_GDN_LAYER': str(args.layer),
        'STRATA_VERIFY_DUMP_GDN_PATH': str((out / f'layer{args.layer}.stgdiag').resolve()),
        'STRATA_VERIFY_DUMP_GDN_POSITIONS': '119',
        'STRATA_VERIFY_DUMP_GDN_BATCH': '1',
    })
    if args.all_layer_commit_state:
        env.update({
            'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': 'all',
            'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': '119',
            'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out / f'{name}-committed-gdn.stgcmt').resolve()),
        })
    if args.boundary_layer is not None:
        env.update({
            'STRATA_VERIFY_DUMP_BOUNDARY_LAYER': str(args.boundary_layer),
            'STRATA_VERIFY_DUMP_BOUNDARY_PATH': str((out / 'boundary.stbndy').resolve()),
            'STRATA_VERIFY_DUMP_BOUNDARY_POSITION': '119',
        })
    if args.moe_layer is not None:
        env.update({
            'STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER': str(args.moe_layer),
            'STRATA_VERIFY_DUMP_MOE_ROUTE_POSITIONS': '119',
            'STRATA_VERIFY_DUMP_MOE_ROUTE_BATCH': '1',
            'STRATA_VERIFY_DUMP_MOE_ROUTE_PATH': str((out / 'moe-routes.jsonl').resolve()),
            'STRATA_VERIFY_DUMP_MOE_PARTS_LAYER': str(args.moe_layer),
            'STRATA_VERIFY_DUMP_MOE_PARTS_POSITIONS': '119',
            'STRATA_VERIFY_DUMP_MOE_PARTS_BATCH': '1',
            'STRATA_VERIFY_DUMP_MOE_PARTS_PATH': str((out / 'moe-parts.stmparts').resolve()),
            'STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER': str(args.moe_layer),
            'STRATA_VERIFY_DUMP_MOE_OUTPUT_POSITIONS': '119',
            'STRATA_VERIFY_DUMP_MOE_OUTPUT_BATCH': '1',
            'STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH': str((out / 'moe-output.stmoe').resolve()),
            'STRATA_CAPTURE_MOE_PATH': str((out / f'{name}.moe-owners.jsonl').resolve()),
            'STRATA_CAPTURE_MOE_LAYER': str(args.moe_layer),
            'STRATA_CAPTURE_MOE_POSITIONS': '119',
            'STRATA_CAPTURE_MOE_ROWS': '64',
        })
    return env

def generate(engine, key, limit, first_token=None, resume_slot0=None):
    ids = []
    for token in engine.generate(prompts[key], limit, {'temperature': 0}, threading.Event()):
        if token is not None:
            ids.append(int(token))
            if first_token is not None and key == 'slot-0' and len(ids) == 48:
                first_token.set()
                if resume_slot0 is None or not resume_slot0.wait(timeout=300):
                    raise TimeoutError('slot 0 was not resumed after competitor queued for control')
    return {'tokens': ids, 'finish': engine.last.get('finish')}

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
    first_token = threading.Event()
    resume_slot0 = threading.Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(generate, batch_engine, 'slot-0', 96, first_token, resume_slot0)
        if not first_token.wait(timeout=300):
            raise TimeoutError('slot 0 did not generate 48 tokens before competitor admission')
        second = pool.submit(generate, batch_engine, 'slot-1', 1)
        deadline = time.monotonic() + 15
        while batch_engine.waiting == 0 and time.monotonic() < deadline:
            time.sleep(0.005)
        if batch_engine.waiting == 0:
            raise TimeoutError('competitor did not queue for engine control before slot 0 resumed')
        resume_slot0.set()
        batch = {'slot-0': first.result(), 'slot-1': second.result()}
finally:
    batch_engine.close()

result = {'capture_layer': args.layer, 'position': 119, 'admit_after_tokens': 48,
          'expert_cache_mib': args.expert_cache_mib,
          'all_layer_commit_state': args.all_layer_commit_state,
          'slot0_paused_until_competitor_queued_for_control': True,
          'prompts': prompts,
          'outputs': {'serial-slot-0': serial, 'batch': batch},
          'slot_0_tokens_equal': serial['tokens'] == batch['slot-0']['tokens']}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'serial_tokens': len(serial['tokens']),
                  'batch_tokens': {key: len(value['tokens']) for key, value in batch.items()},
                  'slot_0_tokens_equal': result['slot_0_tokens_equal']}))
