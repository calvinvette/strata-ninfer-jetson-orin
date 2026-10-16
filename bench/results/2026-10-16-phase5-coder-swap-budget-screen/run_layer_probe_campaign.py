#!/usr/bin/env python3
"""Three randomized paired all-layer Coder short/long diagnostic captures."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

from run_campaign import EXPECTED_BINARY, EXPECTED_MODEL_SHARDS, sha256

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOCK = Path('/tmp') / f'strata-integration-campaign-{os.getuid()}.lock'
CONFIG = ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/baseline-mtp0-config.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261018)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(out)
    cfg = json.loads(CONFIG.read_text())
    binary = Path(cfg['exe'])
    binary_hash = sha256(binary)
    if binary_hash != EXPECTED_BINARY:
        raise RuntimeError(f'unexpected service binary hash: {binary_hash}')
    native = Path(cfg['args'][cfg['args'].index('--native') + 1])
    ple = Path(cfg['args'][cfg['args'].index('--ple-gguf') + 1])
    shards = {native.name: sha256(native), ple.name: sha256(ple)}
    if shards != EXPECTED_MODEL_SHARDS:
        raise RuntimeError(f'unexpected Coder IQ1_M shard hashes: {shards}')

    rng = random.Random(args.seed)
    schedule = []
    for block in range(3):
        arms = [
            {'block': block, 'name': 'delayed-control', 'adapt_every': 100000, 'adapt_swaps': 96},
            {'block': block, 'name': 'swap-8', 'adapt_every': 4, 'adapt_swaps': 8},
        ]
        rng.shuffle(arms)
        schedule.extend(arms)

    out.mkdir(parents=True)
    campaign = {
        'schema': 1,
        'scope': 'Coder IQ1_M all-layer routing capture after short then long prompt',
        'seed': args.seed, 'source_commit': 'e6a55b30f596ecc5173d2eb55a4087662b7ee88f',
        'binary_sha256': binary_hash,
        'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e',
        'model_quantization': 'IQ1_M', 'model_shard_sha256': shards,
        'capture': {'layer': 'all', 'max_rows': 4096, 'requests': ['short-512', 'long-2048']},
        'schedule': schedule, 'status': 'running', 'runs': [],
    }
    path = out / 'campaign.json'

    def save():
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(campaign, indent=2) + '\n')
        temp.replace(path)

    save()
    with LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for item in schedule:
            run = {**item, 'status': 'running', 'started_wall_time': time.time()}
            campaign['runs'].append(run)
            save()
            stem = f"block-{item['block']}-{item['name']}"
            run_dir, supervisor_dir = out / stem, out / f'{stem}-supervisor'
            cmd = [
                'systemd-run', '--user', '--scope', '--collect',
                '-p', 'MemoryMax=28G', '-p', 'IOAccounting=yes',
                sys.executable, str(ROOT / 'tools/integration/run_control.py'),
                '--output', str(supervisor_dir), '--timeout', '1800',
                '--interval', '1', '--sample-clocks', '--', sys.executable,
                str(HERE / 'run_layer_probe.py'), '--adapt-every', str(item['adapt_every']),
                '--adapt-swaps', str(item['adapt_swaps']), '--output', str(run_dir),
            ]
            run['command'] = cmd
            try:
                result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            except BaseException:
                run.update(status='interrupted', finished_wall_time=time.time())
                save()
                raise
            (out / f'{stem}.launch.txt').write_text(result.stdout + result.stderr)
            supervisor = supervisor_dir / 'result.json'
            sup_status = json.loads(supervisor.read_text()).get('status') if supervisor.exists() else None
            analysis = run_dir / 'analysis.json'
            valid = analysis.exists() and json.loads(analysis.read_text()).get('binary_sha256') == binary_hash
            run.update({
                'returncode': result.returncode, 'supervisor_status': sup_status,
                'status': 'pass' if result.returncode == 0 and sup_status == 'pass' and valid else 'fail',
                'finished_wall_time': time.time(), 'binary_sha256_after': sha256(binary),
            })
            save()
            print(f"block={item['block']} arm={item['name']} status={run['status']}", flush=True)
            if run['status'] != 'pass':
                campaign['abort_reason'] = f'stopped at {stem}'
                break
        fcntl.flock(lock, fcntl.LOCK_UN)
    campaign['finished_wall_time'] = time.time()
    campaign['status'] = 'pass' if len(campaign['runs']) == len(schedule) and all(
        run['status'] == 'pass' for run in campaign['runs']) else 'fail'
    save()
    return 0 if campaign['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
