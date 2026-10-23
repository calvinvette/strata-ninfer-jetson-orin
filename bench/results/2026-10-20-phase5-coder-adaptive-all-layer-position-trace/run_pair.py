#!/usr/bin/env python3
"""Run a randomized current-binary Coder delayed/adaptive correctness pair."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7'
EXPECTED_MODEL = {
    'Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf': 'e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad',
    'Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf': '316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113',
}
ARMS = [
    {'name': 'delayed-control', 'adapt_every': 100000, 'adapt_swaps': 96},
    {'name': 'adaptive-cap8', 'adapt_every': 4, 'adapt_swaps': 8},
]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=20261030)
    ap.add_argument('--continuations', type=int, default=1)
    ap.add_argument('--sequence', choices=('short-long-short', 'short-short-short'),
                    default='short-long-short',
                    help='same-service request history used for the recovery comparison')
    ap.add_argument('--generated-tokens', type=int, default=16,
                    help='maximum generated tokens per request (default: 16)')
    ap.add_argument('--workload-file', type=Path,
                    help='optional workload JSON (defaults to the pinned Phase 5 prompt set)')
    ap.add_argument('--workload-index', type=int, default=0,
                    help='workload entry index in --workload-file (default: 0)')
    ap.add_argument('--long-token-limit', type=int, default=0,
                    help='optional suffix length for the long prompt (0 keeps all encoded tokens)')
    ap.add_argument('--native-cpu-q8-1-dot', default=os.environ.get('STRATA_NATIVE_CPU_Q8_1_DOT', 'all'),
                    help='opt-in CPU/CUDA Q8_1 selector passed to both service arms (default: all)')
    ap.add_argument('--native-cpu-q8-1-reciprocal-silu-layer', type=int,
                    help='opt-in reciprocal-SiLU expression for Q8_1 native experts at one layer')
    ap.add_argument('--native-cpu-q8-1-reciprocal-silu-expert', type=int,
                    help='optionally restrict reciprocal-SiLU to one model expert ID')
    ap.add_argument('--prompt-cache', type=int,
                    help='optional prompt-cache capacity override for both service arms')
    ap.add_argument('--capture-moe-positions', default='511')
    ap.add_argument('--capture-moe-rows', type=int, default=192,
                    help='maximum selected all-layer expert rows to retain (1-4096; default covers four requests)')
    ap.add_argument('--capture-cpu-output-layer', type=int,
                    help='capture CPU expert rows from one selected dispatch in each arm')
    ap.add_argument('--capture-cpu-output-dispatch', type=int,
                    help='dispatch ID for the optional CPU expert output capture')
    ap.add_argument('--capture-cpu-output-position', type=int, default=511,
                    help='position required in the selected CPU output dispatch (default: 511)')
    ap.add_argument('--capture-verify-moe-layer', type=int)
    ap.add_argument('--verify-moe-positions', default='511')
    ap.add_argument('--verify-moe-input-layers', choices=('same', 'all'), default='same')
    ap.add_argument('--capture-verify-gdn-layer', type=int)
    ap.add_argument('--verify-gdn-positions', default='511')
    ap.add_argument('--capture-verify-gdn-state-layer', type=int,
                    help='capture raw verifier pre/post state for one GDN model layer')
    ap.add_argument('--gdn-state-positions', default='511')
    ap.add_argument('--capture-boundary-layer', type=int,
                    help='capture residual/hyperconnection values around this layer boundary')
    ap.add_argument('--boundary-position', type=int, default=511)
    ap.add_argument('--capture-gdn-commit-state-layer',
                    help="capture one GDN layer or 'all' after accepted windows")
    ap.add_argument('--gdn-commit-state-positions', default='')
    ap.add_argument('--trace-prefill-gdn-state-layer', type=int,
                    help='capture full GDN state at every prefill chunk boundary for one layer')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    if (a.capture_cpu_output_layer is None) != (a.capture_cpu_output_dispatch is None):
        ap.error('CPU output capture requires both --capture-cpu-output-layer and --capture-cpu-output-dispatch')
    if a.capture_cpu_output_layer is not None and min(
            a.capture_cpu_output_layer, a.capture_cpu_output_dispatch, a.capture_cpu_output_position) < 0:
        ap.error('CPU output capture layer, dispatch and position must be non-negative')
    if a.continuations < 0:
        ap.error('--continuations must be non-negative')
    if a.generated_tokens <= 0:
        ap.error('--generated-tokens must be positive')
    if a.workload_index < 0:
        ap.error('--workload-index must be non-negative')
    if a.long_token_limit < 0:
        ap.error('--long-token-limit must be non-negative')
    workload_path = a.workload_file.expanduser().resolve() if a.workload_file is not None else BASE / 'workloads.json'
    if not workload_path.is_file():
        ap.error(f'workload file does not exist: {workload_path}')
    workload_doc = json.loads(workload_path.read_text())
    workload_rows = workload_doc.get('workloads', [])
    if a.workload_index >= len(workload_rows):
        ap.error(f'workload index {a.workload_index} is outside {len(workload_rows)} entries')
    if a.capture_moe_rows <= 0 or a.capture_moe_rows > 4096:
        ap.error('--capture-moe-rows must be between 1 and 4096')
    if a.capture_boundary_layer is not None and a.capture_boundary_layer < 0:
        ap.error('--capture-boundary-layer must be non-negative')
    if a.boundary_position < 0:
        ap.error('--boundary-position must be non-negative')
    if a.prompt_cache is not None and a.prompt_cache < 0:
        ap.error('--prompt-cache must be non-negative')
    if a.native_cpu_q8_1_reciprocal_silu_layer is not None and a.native_cpu_q8_1_reciprocal_silu_layer < 0:
        ap.error('--native-cpu-q8-1-reciprocal-silu-layer must be non-negative')
    if a.native_cpu_q8_1_reciprocal_silu_expert is not None and a.native_cpu_q8_1_reciprocal_silu_expert < 0:
        ap.error('--native-cpu-q8-1-reciprocal-silu-expert must be non-negative')
    if a.native_cpu_q8_1_reciprocal_silu_expert is not None and a.native_cpu_q8_1_reciprocal_silu_layer is None:
        ap.error('--native-cpu-q8-1-reciprocal-silu-expert requires --native-cpu-q8-1-reciprocal-silu-layer')
    try:
        capture_positions = [int(value) for value in a.capture_moe_positions.split(',')]
    except ValueError:
        ap.error('--capture-moe-positions must be comma-separated non-negative integers')
    if not capture_positions or any(value < 0 for value in capture_positions) or \
            capture_positions != sorted(set(capture_positions)):
        ap.error('--capture-moe-positions must be strictly increasing non-negative integers')
    try:
        verify_positions = [int(value) for value in a.verify_moe_positions.split(',')]
    except ValueError:
        ap.error('--verify-moe-positions must be comma-separated non-negative integers')
    if not verify_positions or any(value < 0 for value in verify_positions) or \
            verify_positions != sorted(set(verify_positions)):
        ap.error('--verify-moe-positions must be strictly increasing non-negative integers')
    try:
        gdn_positions = [int(value) for value in a.verify_gdn_positions.split(',')]
    except ValueError:
        ap.error('--verify-gdn-positions must be comma-separated non-negative integers')
    if not gdn_positions or any(value < 0 for value in gdn_positions) or \
            gdn_positions != sorted(set(gdn_positions)):
        ap.error('--verify-gdn-positions must be strictly increasing non-negative integers')
    try:
        gdn_state_positions = [int(value) for value in a.gdn_state_positions.split(',')]
    except ValueError:
        ap.error('--gdn-state-positions must be comma-separated non-negative integers')
    if not gdn_state_positions or any(value < 0 for value in gdn_state_positions) or \
            gdn_state_positions != sorted(set(gdn_state_positions)):
        ap.error('--gdn-state-positions must be strictly increasing non-negative integers')
    if a.capture_verify_gdn_state_layer is None and gdn_state_positions != [511]:
        ap.error('--gdn-state-positions requires --capture-verify-gdn-state-layer')
    if a.capture_verify_gdn_layer is not None and a.capture_verify_gdn_layer < 0:
        ap.error('--capture-verify-gdn-layer must be non-negative')
    if a.capture_verify_gdn_state_layer is not None and a.capture_verify_gdn_state_layer < 0:
        ap.error('--capture-verify-gdn-state-layer must be non-negative')
    if a.trace_prefill_gdn_state_layer is not None and a.trace_prefill_gdn_state_layer < 0:
        ap.error('--trace-prefill-gdn-state-layer must be non-negative')
    try:
        commit_positions = [int(value) for value in a.gdn_commit_state_positions.split(',') if value]
    except ValueError:
        ap.error('--gdn-commit-state-positions must be comma-separated non-negative integers')
    if a.capture_gdn_commit_state_layer is None and commit_positions:
        ap.error('--gdn-commit-state-positions requires --capture-gdn-commit-state-layer')
    capture_all_gdn_layers = a.capture_gdn_commit_state_layer == 'all'
    try:
        if a.capture_gdn_commit_state_layer is not None and not capture_all_gdn_layers:
            a.capture_gdn_commit_state_layer = int(a.capture_gdn_commit_state_layer)
    except ValueError:
        ap.error('--capture-gdn-commit-state-layer must be a non-negative layer or all')
    if a.capture_gdn_commit_state_layer is not None and (
            (not capture_all_gdn_layers and a.capture_gdn_commit_state_layer < 0) or not commit_positions or
            any(value < 0 for value in commit_positions) or commit_positions != sorted(set(commit_positions))):
        ap.error('--capture-gdn-commit-state-layer requires a layer and increasing non-negative positions')
    if a.output.exists():
        ap.error('output directory already exists')
    cfg = json.loads((BASE / 'config.json').read_text())
    binary = Path(cfg['exe'])
    native = Path(cfg['args'][cfg['args'].index('--native') + 1])
    ple = Path(cfg['args'][cfg['args'].index('--ple-gguf') + 1])
    for model in (native, ple):
        if digest(model) != EXPECTED_MODEL.get(model.name):
            raise RuntimeError(f'model checksum mismatch: {model}')
    campaign = {
        'schema': 1, 'status': 'planned', 'seed': a.seed,
        'scope': 'one randomized same-service request-sequence correctness pair with optional continuation; delayed adaptation versus cap-8 adaptive swaps',
        'sequence': a.sequence,
        'prompt_workload_file': str(workload_path),
        'prompt_workload_file_sha256': digest(workload_path),
        'prompt_workload_index': a.workload_index,
        'prompt_workload_cell': workload_rows[a.workload_index].get('cell'),
        'long_token_limit': a.long_token_limit,
        'continuations': a.continuations, 'generated_tokens': a.generated_tokens,
        'capture_moe_positions': capture_positions,
        'capture_moe_rows': a.capture_moe_rows,
        'capture_cpu_output_layer': a.capture_cpu_output_layer,
        'capture_cpu_output_dispatch': a.capture_cpu_output_dispatch,
        'capture_cpu_output_position': a.capture_cpu_output_position if a.capture_cpu_output_layer is not None else None,
        'capture_verify_moe_layer': a.capture_verify_moe_layer,
        'verify_moe_positions': verify_positions if a.capture_verify_moe_layer is not None else None,
        'verify_moe_input_layers': a.verify_moe_input_layers if a.capture_verify_moe_layer is not None else None,
        'capture_verify_gdn_layer': a.capture_verify_gdn_layer,
        'verify_gdn_positions': gdn_positions if a.capture_verify_gdn_layer is not None else None,
        'capture_verify_gdn_state_layer': a.capture_verify_gdn_state_layer,
        'gdn_state_positions': gdn_state_positions if a.capture_verify_gdn_state_layer is not None else None,
        'capture_boundary_layer': a.capture_boundary_layer,
        'boundary_position': a.boundary_position if a.capture_boundary_layer is not None else None,
        'capture_gdn_commit_state_layer': a.capture_gdn_commit_state_layer,
        'gdn_commit_state_positions': commit_positions if a.capture_gdn_commit_state_layer is not None else None,
        'trace_prefill_gdn_state_layer': a.trace_prefill_gdn_state_layer,
        'repository_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'runner_source_sha256': {
            'run_pair.py': digest(HERE / 'run_pair.py'),
            'run_one.py': digest(HERE / 'run_one.py'),
        },
        'binary_sha256': digest(binary), 'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e', 'quantization': 'IQ1_M',
        'native_cpu_q8_1_dot': a.native_cpu_q8_1_dot,
        'native_cpu_q8_1_reciprocal_silu_layer': a.native_cpu_q8_1_reciprocal_silu_layer,
        'native_cpu_q8_1_reciprocal_silu_expert': a.native_cpu_q8_1_reciprocal_silu_expert,
        'prompt_cache_override': a.prompt_cache,
        'model_shard_sha256': EXPECTED_MODEL, 'runs': [],
    }
    schedule = list(ARMS)
    random.Random(a.seed).shuffle(schedule)
    campaign['order'] = [row['name'] for row in schedule]
    print(json.dumps({'order': campaign['order'], 'binary_sha256': campaign['binary_sha256']}, indent=2))
    if not a.run:
        return 0
    a.output.mkdir(parents=True)
    campaign['status'] = 'running'
    def save():
        temp = a.output / 'campaign.tmp'
        temp.write_text(json.dumps(campaign, indent=2) + '\n')
        temp.replace(a.output / 'campaign.json')
    save()
    py = '/home/calvin/.local/python/bin/python3'
    supervisor = ROOT / 'tools/integration/run_control.py'
    runner = HERE / 'run_one.py'
    for arm in schedule:
        d = a.output / arm['name']
        d.mkdir()
        sup = d / 'supervisor'
        result = d / 'result'
        cmd = [py, str(supervisor), '--output', str(sup), '--timeout', '1800', '--interval', '1', '--sample-clocks', '--',
               py, str(runner), '--adapt-every', str(arm['adapt_every']), '--adapt-swaps', str(arm['adapt_swaps']),
               '--continuations', str(a.continuations), '--generated-tokens', str(a.generated_tokens),
               '--sequence', a.sequence,
               '--native-cpu-q8-1-dot', a.native_cpu_q8_1_dot,
               '--capture-moe-positions', a.capture_moe_positions,
               '--capture-moe-rows', str(a.capture_moe_rows),
               '--output', str(result)]
        if a.workload_file is not None:
            cmd.extend(['--workload-file', str(workload_path), '--workload-index', str(a.workload_index)])
        if a.long_token_limit:
            cmd.extend(['--long-token-limit', str(a.long_token_limit)])
        if a.native_cpu_q8_1_reciprocal_silu_layer is not None:
            cmd.extend(['--native-cpu-q8-1-reciprocal-silu-layer',
                        str(a.native_cpu_q8_1_reciprocal_silu_layer)])
        if a.native_cpu_q8_1_reciprocal_silu_expert is not None:
            cmd.extend(['--native-cpu-q8-1-reciprocal-silu-expert',
                        str(a.native_cpu_q8_1_reciprocal_silu_expert)])
        if a.prompt_cache is not None:
            cmd.extend(['--prompt-cache', str(a.prompt_cache)])
        if a.capture_cpu_output_layer is not None:
            cmd.extend(['--capture-cpu-output-layer', str(a.capture_cpu_output_layer),
                        '--capture-cpu-output-dispatch', str(a.capture_cpu_output_dispatch),
                        '--capture-cpu-output-position', str(a.capture_cpu_output_position)])
        if a.capture_verify_moe_layer is not None:
            cmd.extend(['--capture-verify-moe-layer', str(a.capture_verify_moe_layer),
                        '--verify-moe-positions', a.verify_moe_positions,
                        '--verify-moe-input-layers', a.verify_moe_input_layers])
        if a.capture_verify_gdn_layer is not None:
            cmd.extend(['--capture-verify-gdn-layer', str(a.capture_verify_gdn_layer),
                        '--verify-gdn-positions', a.verify_gdn_positions])
        if a.capture_verify_gdn_state_layer is not None:
            cmd.extend(['--capture-verify-gdn-state-layer', str(a.capture_verify_gdn_state_layer),
                        '--gdn-state-positions', a.gdn_state_positions,
                        '--gdn-state-output', str(result / 'gdn-state.bin')])
        if a.capture_boundary_layer is not None:
            cmd.extend(['--capture-boundary-layer', str(a.capture_boundary_layer),
                        '--boundary-position', str(a.boundary_position)])
        if a.capture_gdn_commit_state_layer is not None:
            cmd.extend(['--capture-gdn-commit-state-layer', str(a.capture_gdn_commit_state_layer),
                        '--gdn-commit-state-positions', a.gdn_commit_state_positions,
                        '--gdn-commit-state-output', str(result / 'gdn-commit-state.bin')])
        if a.trace_prefill_gdn_state_layer is not None:
            cmd.extend(['--trace-prefill-gdn-state-layer', str(a.trace_prefill_gdn_state_layer),
                        '--prefill-gdn-state-output', str(result / 'prefill-gdn-state.bin')])
        (d / 'launch.txt').write_text('systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes ' + ' '.join(cmd) + '\n')
        start = time.time()
        completed = subprocess.run(['systemd-run', '--user', '--scope', '--collect', '-p', 'MemoryMax=28G', '-p', 'IOAccounting=yes', *cmd], cwd=ROOT, capture_output=True, text=True)
        with (d / 'launch.txt').open('a') as f:
            f.write(completed.stdout + completed.stderr)
        sr = json.loads((sup / 'result.json').read_text()) if (sup / 'result.json').exists() else {}
        analysis = json.loads((result / 'analysis.json').read_text()) if (result / 'analysis.json').exists() else {}
        ok = completed.returncode == 0 and sr.get('status') == 'pass' and analysis.get('binary_sha256') == campaign['binary_sha256']
        row = {**arm, 'status': 'pass' if ok else 'fail', 'launcher_returncode': completed.returncode,
               'supervisor_status': sr.get('status'), 'minimum_available_bytes': sr.get('minimum_available_bytes'),
               'minimum_admission_available_bytes': sr.get('minimum_admission_available_bytes'),
               'elapsed_s': sr.get('elapsed_s'), 'analysis': analysis, 'wall_start_s': start}
        campaign['runs'].append(row)
        save()
        if not ok:
            campaign['status'] = 'fail'
            save()
            return 1
    campaign['status'] = 'pass'
    campaign['finished_wall_time_s'] = time.time()
    save()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
