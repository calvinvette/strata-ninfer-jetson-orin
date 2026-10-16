#!/usr/bin/env python3
"""Compare delayed control and cap 8 through one extra post-recovery request."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from prepare_campaign import make_schedule
from run_campaign import EXPECTED_BINARY, EXPECTED_MODEL_SHARDS, sha256

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOCK = Path('/tmp') / f'strata-integration-campaign-{os.getuid()}.lock'
CONFIG = ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/baseline-mtp0-config.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261017)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(out)
    config = json.loads(CONFIG.read_text())
    binary = Path(config['exe'])
    binary_hash = sha256(binary)
    if binary_hash != EXPECTED_BINARY:
        raise RuntimeError(f'unexpected service binary hash: {binary_hash}')
    native = Path(config['args'][config['args'].index('--native') + 1])
    ple = Path(config['args'][config['args'].index('--ple-gguf') + 1])
    model_hashes = {native.name: sha256(native), ple.name: sha256(ple)}
    if model_hashes != EXPECTED_MODEL_SHARDS:
        raise RuntimeError(f'unexpected model shard hashes: {model_hashes}')

    # The full schedule randomizes each four-arm block. Keep its randomized
    # delayed-control/cap-8 order while excluding unrelated caps.
    schedule = [row for row in make_schedule(args.seed)
                if row['name'] in {'delayed-control', 'swap-8'}]
    out.mkdir(parents=True)
    campaign = {
        'schema': 1,
        'scope': 'Coder IQ1_M post-recovery continuation: delayed control vs swap cap 8',
        'seed': args.seed,
        'binary_sha256': binary_hash,
        'source_commit': '40379a6f',
        'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e',
        'model_quantization': 'IQ1_M',
        'model_shard_sha256': model_hashes,
        'continuation_requests': 1,
        'schedule': schedule,
        'status': 'running',
        'runs': [],
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
                '--output', str(supervisor_dir), '--timeout', '1200',
                '--interval', '1', '--sample-clocks', '--', sys.executable,
                str(HERE / 'run_one.py'), '--adapt-every', str(item['adapt_every']),
                '--adapt-swaps', str(item['adapt_swaps']), '--continuations', '1',
                '--output', str(run_dir),
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
                'returncode': result.returncode,
                'supervisor_status': sup_status,
                'status': 'pass' if result.returncode == 0 and sup_status == 'pass' and valid else 'fail',
                'finished_wall_time': time.time(),
                'binary_sha256_after': sha256(binary),
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
