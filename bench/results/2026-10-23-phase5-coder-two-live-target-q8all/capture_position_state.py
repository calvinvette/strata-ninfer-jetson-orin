#!/usr/bin/env python3
"""Capture committed GDN states at position 133 under Q8_1-all selection."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, remove_arg, replace_arg

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--position', type=int, default=133)
p.add_argument('--positions', help='comma-separated state capture positions; overrides --position')
p.add_argument('--expert-cache-mib', type=int, default=1500)
p.add_argument('--layer', default='all', help='GDN model layer or all')
p.add_argument('--stage-layer', type=int, help='also capture GDN intermediate fields for this layer')
opts = p.parse_args()
positions = opts.positions or str(opts.position)
out = opts.output.resolve()
out.mkdir(parents=True, exist_ok=False)
base = Path(__file__).resolve().parent
cfg = json.loads((base.parent/'2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json').read_text())
args = list(cfg['args'])
for key in ('--mtp', '--mtp-max-t', '--adapt-every', '--adapt-accepted-only'):
    remove_arg(args, key)
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', str(opts.expert_cache_mib))
replace_arg(args, '--prompt-cache', '6')
prompts = prepared_prompts(cfg, 2)

def make_env(name):
    env = child_env(cfg)
    env.update({'STRATA_NATIVE_CPU_Q8_1_DOT': 'all', 'STRATA_IQ_MT_MIN': '1',
                'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': str(opts.layer),
                'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': positions,
                'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out/f'{name}.stgcmt').resolve())})
    if opts.stage_layer is not None:
        env.update({'STRATA_VERIFY_DUMP_GDN_LAYER': str(opts.stage_layer),
                    'STRATA_VERIFY_DUMP_GDN_PATH': str((out/f'{name}.stgdiag').resolve()),
                    'STRATA_VERIFY_DUMP_GDN_POSITIONS': positions,
                    'STRATA_VERIFY_DUMP_GDN_BATCH': '1'})
    return env

def generate(engine, key):
    tokens = [int(t) for t in engine.generate(prompts[key], 96, {'temperature': 0}, threading.Event()) if t is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial = StrataEngine(cfg['exe'], args, cwd=cfg.get('cwd'), log=str(out/'serial-slot-1.log'), env=make_env('serial'))
try:
    serial_out = generate(serial, 'slot-1')
finally:
    serial.close()

batch = StrataEngine(cfg['exe'], args+['--batch', '2'], cwd=cfg.get('cwd'),
                     log=str(out/'batch.log'), env=make_env('batch'))
try:
    if batch.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {batch.batch}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {key: pool.submit(generate, batch, key) for key in prompts}
        batch_out = {key: job.result() for key, job in jobs.items()}
finally:
    batch.close()

result = {'capture_positions': [int(x) for x in positions.split(',')], 'target_slot': 1,
          'serial_slot_1': serial_out, 'batch': batch_out, 'prompts': prompts,
          'profile': {'live_requests': 2, 'batch_slots': 2, 'mtp': False,
                      'expert_cache_mib': opts.expert_cache_mib,
                      'gdn_layer': opts.layer,
                      'stage_layer': opts.stage_layer,
                      'STRATA_NATIVE_CPU_Q8_1_DOT': 'all', 'STRATA_IQ_MT_MIN': '1'}}
(out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'positions': [int(x) for x in positions.split(',')], 'serial_tokens': len(serial_out['tokens']),
                  'batch_tokens': {k: len(v['tokens']) for k,v in batch_out.items()}}))
