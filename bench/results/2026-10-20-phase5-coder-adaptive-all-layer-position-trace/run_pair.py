#!/usr/bin/env python3
"""Run a randomized current-binary Coder delayed/adaptive correctness pair."""
import argparse
import hashlib
import json
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
    ap.add_argument('--generated-tokens', type=int, default=16,
                    help='maximum generated tokens per request (default: 16)')
    ap.add_argument('--capture-moe-positions', default='511')
    ap.add_argument('--capture-verify-moe-layer', type=int)
    ap.add_argument('--verify-moe-positions', default='511')
    ap.add_argument('--capture-verify-gdn-layer', type=int)
    ap.add_argument('--verify-gdn-positions', default='511')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    if a.continuations < 0:
        ap.error('--continuations must be non-negative')
    if a.generated_tokens <= 0:
        ap.error('--generated-tokens must be positive')
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
    if a.capture_verify_gdn_layer is not None and a.capture_verify_gdn_layer < 0:
        ap.error('--capture-verify-gdn-layer must be non-negative')
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
        'scope': 'one randomized same-service short/long/short correctness pair with optional continuation; delayed adaptation versus cap-8 adaptive swaps',
        'continuations': a.continuations, 'generated_tokens': a.generated_tokens,
        'capture_moe_positions': capture_positions,
        'capture_verify_moe_layer': a.capture_verify_moe_layer,
        'verify_moe_positions': verify_positions if a.capture_verify_moe_layer is not None else None,
        'capture_verify_gdn_layer': a.capture_verify_gdn_layer,
        'verify_gdn_positions': gdn_positions if a.capture_verify_gdn_layer is not None else None,
        'repository_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'binary_sha256': digest(binary), 'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e', 'quantization': 'IQ1_M',
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
               '--capture-moe-positions', a.capture_moe_positions,
               '--output', str(result)]
        if a.capture_verify_moe_layer is not None:
            cmd.extend(['--capture-verify-moe-layer', str(a.capture_verify_moe_layer),
                        '--verify-moe-positions', a.verify_moe_positions])
        if a.capture_verify_gdn_layer is not None:
            cmd.extend(['--capture-verify-gdn-layer', str(a.capture_verify_gdn_layer),
                        '--verify-gdn-positions', a.verify_gdn_positions])
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
