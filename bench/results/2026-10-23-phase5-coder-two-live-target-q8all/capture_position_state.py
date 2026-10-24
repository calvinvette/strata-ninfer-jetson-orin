#!/usr/bin/env python3
"""Capture selected persistent state and optional stage/MoE diagnostics under Q8_1-all selection."""
import argparse
import hashlib
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
p.add_argument('--expert-cache-slots', '--expert-cache-mib', type=int, default=1500,
               help='requested Strata expert-cache slot count (legacy MiB alias accepted)')
p.add_argument('--expert-profile', type=Path,
               help='optional static residency profile used by serial and batch controls')
p.add_argument('--exp2f-silu-layer', type=int,
               help='opt in to host exp2f SiLU for CPU Q8_1 experts on this model layer')
p.add_argument('--exp2f-silu-expert', type=int,
               help='optional model expert ID filter for --exp2f-silu-layer')
p.add_argument('--layer', default='all', help='GDN model layer or all')
p.add_argument('--stage-layer', type=int, help='also capture GDN intermediate fields for this layer')
p.add_argument('--moe-layer', type=int, help='also capture MoE route/parts/output and owner records for this layer')
p.add_argument('--boundary-layer', type=int,
               help='also capture verifier residual boundary before/after this layer')
p.add_argument('--batch-live', type=int, choices=(1, 2), default=2,
               help='number of concurrent requests submitted to the batch verifier')
p.add_argument('--serial-slot', choices=('0', '1', 'both'), default='1',
               help='serial prompt control(s) to capture; default preserves the slot-1-only run')
p.add_argument('--generated-tokens', type=int, default=96,
               help='generated tokens per serial and batch request')
p.add_argument('--prompt-offset', type=int, default=0,
               help='select two consecutive prepared integration prompts starting at this task index')
p.add_argument('--reverse-prompt-order', action='store_true',
               help='assign the same selected prompt pair to the opposite logical slots')
p.add_argument('--trace-state-hashes', action='store_true',
               help='log accepted-prefix GDN/QSA fingerprints at every committed position')
p.add_argument('--trace-batch-gdn-hashes', action='store_true',
               help='hash committed batch GDN allocations at each verifier position')
p.add_argument('--batch-gdn-hash-from', type=int, default=0)
p.add_argument('--batch-gdn-hash-to', type=int, default=4096)
p.add_argument('--trace-batch-qsa-hashes', action='store_true',
               help='hash committed batch QSA allocations at each accepted position')
p.add_argument('--batch-qsa-hash-from', type=int, default=0)
p.add_argument('--batch-qsa-hash-to', type=int, default=4096)
opts = p.parse_args()
if opts.generated_tokens < 1:
    p.error('--generated-tokens must be positive')
if opts.prompt_offset < 0:
    p.error('--prompt-offset must be nonnegative')
if opts.exp2f_silu_expert is not None and opts.exp2f_silu_layer is None:
    p.error('--exp2f-silu-expert requires --exp2f-silu-layer')
positions = opts.positions or str(opts.position)
if opts.boundary_layer is not None and ',' in positions:
    p.error('--boundary-layer currently supports one --position at a time')
out = opts.output.resolve()
out.mkdir(parents=True, exist_ok=False)
base = Path(__file__).resolve().parent
cfg = json.loads((base.parent/'2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json').read_text())
args = list(cfg['args'])
for key in ('--mtp', '--mtp-max-t', '--adapt-every', '--adapt-accepted-only'):
    remove_arg(args, key)
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', str(opts.expert_cache_slots))
if opts.expert_profile is not None:
    replace_arg(args, '--expert-profile', str(opts.expert_profile.resolve()))
replace_arg(args, '--prompt-cache', '6')
prepared = prepared_prompts(cfg, opts.prompt_offset + 2)
prompts = {f'slot-{i}': prepared[f'slot-{opts.prompt_offset + i}'] for i in range(2)}
if opts.reverse_prompt_order:
    prompts = {'slot-0': prompts['slot-1'], 'slot-1': prompts['slot-0']}
batch_prompts = prompts if opts.batch_live == 2 else {'slot-1': prompts['slot-1']}

def make_env(name, is_batch=False):
    env = child_env(cfg)
    env.update({'STRATA_NATIVE_CPU_Q8_1_DOT': 'all', 'STRATA_IQ_MT_MIN': '1',
                'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER': str(opts.layer),
                'STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS': positions,
                'STRATA_VERIFY_DUMP_GDN_COMMIT_PATH': str((out/f'{name}.stgcmt').resolve())})
    if opts.exp2f_silu_layer is not None:
        env['STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER'] = str(opts.exp2f_silu_layer)
    if opts.exp2f_silu_expert is not None:
        env['STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT'] = str(opts.exp2f_silu_expert)
    if opts.stage_layer is not None:
        env.update({'STRATA_VERIFY_DUMP_GDN_LAYER': str(opts.stage_layer),
                    'STRATA_VERIFY_DUMP_GDN_PATH': str((out/f'{name}.stgdiag').resolve()),
                    'STRATA_VERIFY_DUMP_GDN_POSITIONS': positions,
                    'STRATA_VERIFY_DUMP_GDN_BATCH': '1'})
    if opts.moe_layer is not None:
        env.update({'STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER': str(opts.moe_layer),
                    'STRATA_VERIFY_DUMP_MOE_ROUTE_POSITIONS': positions,
                    'STRATA_VERIFY_DUMP_MOE_ROUTE_BATCH': '1',
                    'STRATA_VERIFY_DUMP_MOE_ROUTE_PATH': str((out/f'{name}.routes.jsonl').resolve()),
                    'STRATA_VERIFY_DUMP_MOE_PARTS_LAYER': str(opts.moe_layer),
                    'STRATA_VERIFY_DUMP_MOE_PARTS_POSITIONS': positions,
                    'STRATA_VERIFY_DUMP_MOE_PARTS_BATCH': '1',
                    'STRATA_VERIFY_DUMP_MOE_PARTS_PATH': str((out/f'{name}.parts.stmparts').resolve()),
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER': str(opts.moe_layer),
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_POSITIONS': positions,
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_BATCH': '1',
                    'STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH': str((out/f'{name}.output.stmoe').resolve()),
                    'STRATA_CAPTURE_MOE_LAYER': str(opts.moe_layer),
                    'STRATA_CAPTURE_MOE_POSITIONS': positions,
                    'STRATA_CAPTURE_MOE_ROWS': '64',
                    'STRATA_CAPTURE_MOE_PATH': str((out/f'{name}.owners.jsonl').resolve())})
        if is_batch:
            env['STRATA_INTEGRATION_TRACE'] = '1'
    if opts.boundary_layer is not None:
        env.update({'STRATA_VERIFY_DUMP_BOUNDARY_LAYER': str(opts.boundary_layer),
                    'STRATA_VERIFY_DUMP_BOUNDARY_PATH': str((out/f'{name}.stbndy').resolve()),
                    'STRATA_VERIFY_DUMP_BOUNDARY_POSITION': positions})
    if opts.trace_state_hashes:
        env.update({'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_STATE_HASH_GDN': '1',
                    'STRATA_STATE_HASH_QSA_LAYERS': '1'})
    if opts.trace_batch_gdn_hashes:
        env.update({'STRATA_BATCH_GDN_HASH_PATH': str((out/f'{name}.batch-gdn-hashes.txt').resolve()),
                    'STRATA_BATCH_GDN_HASH_FROM': str(opts.batch_gdn_hash_from),
                    'STRATA_BATCH_GDN_HASH_TO': str(opts.batch_gdn_hash_to)})
    if opts.trace_batch_qsa_hashes:
        env.update({'STRATA_BATCH_QSA_HASH_PATH': str((out/f'{name}.batch-qsa-hashes.txt').resolve()),
                    'STRATA_BATCH_QSA_HASH_FROM': str(opts.batch_qsa_hash_from),
                    'STRATA_BATCH_QSA_HASH_TO': str(opts.batch_qsa_hash_to)})
    return env

def generate(engine, key):
    tokens = [int(t) for t in engine.generate(prompts[key], opts.generated_tokens, {'temperature': 0}, threading.Event()) if t is not None]
    return {'tokens': tokens, 'finish': engine.last.get('finish')}

serial_slots = ('slot-0', 'slot-1') if opts.serial_slot == 'both' else (f'slot-{opts.serial_slot}',)
serial_out = {}
for key in serial_slots:
    stem = f'serial-{key}' if opts.serial_slot == 'both' else 'serial'
    serial = StrataEngine(cfg['exe'], args, cwd=cfg.get('cwd'), log=str(out/f'{stem}.log'),
                          env=make_env(stem))
    try:
        serial_out[key] = generate(serial, key)
    finally:
        serial.close()

batch = StrataEngine(cfg['exe'], args+['--batch', '2'], cwd=cfg.get('cwd'),
                     log=str(out/'batch.log'), env=make_env('batch', is_batch=True))
try:
    if batch.batch != 2:
        raise RuntimeError(f'expected two batch slots, got {batch.batch}')
    with ThreadPoolExecutor(max_workers=opts.batch_live) as pool:
        jobs = {key: pool.submit(generate, batch, key) for key in batch_prompts}
        batch_out = {key: job.result() for key, job in jobs.items()}
finally:
    batch.close()

result = {'capture_positions': [int(x) for x in positions.split(',')],
          'target_slot': None if opts.serial_slot == 'both' else int(opts.serial_slot),
          'serial_control': opts.serial_slot,
          'serial': serial_out, 'serial_slot_1': serial_out.get('slot-1'),
          'batch': batch_out, 'prompts': prompts,
          'expert_profile': ({'path': str(opts.expert_profile.resolve()),
                              'sha256': hashlib.sha256(opts.expert_profile.read_bytes()).hexdigest()}
                             if opts.expert_profile is not None else None),
          'profile': {'live_requests': opts.batch_live, 'batch_slots': 2, 'mtp': False,
                      'expert_cache_slots': opts.expert_cache_slots,
                      'generated_tokens': opts.generated_tokens,
                      'prompt_offset': opts.prompt_offset,
                      'reverse_prompt_order': opts.reverse_prompt_order,
                      'serial_slot_controls': list(serial_slots),
                      'gdn_layer': opts.layer,
                      'stage_layer': opts.stage_layer,
                      'moe_layer': opts.moe_layer,
                      'boundary_layer': opts.boundary_layer,
                      'trace_state_hashes': opts.trace_state_hashes,
                      'trace_batch_gdn_hashes': opts.trace_batch_gdn_hashes,
                      'batch_gdn_hash_range': [opts.batch_gdn_hash_from, opts.batch_gdn_hash_to],
                      'trace_batch_qsa_hashes': opts.trace_batch_qsa_hashes,
                      'batch_qsa_hash_range': [opts.batch_qsa_hash_from, opts.batch_qsa_hash_to],
                      'STRATA_NATIVE_CPU_Q8_1_DOT': 'all', 'STRATA_IQ_MT_MIN': '1'}}
result['exp2f_silu'] = ({'layer': opts.exp2f_silu_layer,
                         'expert': opts.exp2f_silu_expert}
                        if opts.exp2f_silu_layer is not None else None)
(out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'positions': [int(x) for x in positions.split(',')],
                  'serial_tokens': {key: len(value['tokens']) for key, value in serial_out.items()},
                  'batch_tokens': {k: len(v['tokens']) for k,v in batch_out.items()}}))
