#!/usr/bin/env python3
"""Randomized captured/eager × MTP off/window2 Q2_0 screening campaign."""
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUN_CONTROL = ROOT / 'tools/integration/run_control.py'
API_BLOCK = ROOT / 'tools/integration/api_control_block.py'
CONDITIONS = ('captured-mtp0', 'eager-mtp0', 'captured-mtp2', 'eager-mtp2')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--blocks', type=int, default=3)
    ap.add_argument('--seed', type=int, default=202610141)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.blocks < 3 or args.output.exists():
        ap.error('screen requires at least three blocks and a new output path')
    configs = {name: HERE / f'config-{name}.json' for name in CONDITIONS}
    for condition, path in configs.items():
        cfg = json.loads(path.read_text())
        argv = cfg['args']
        mtp = int(condition.split('mtp')[1])
        eager = condition.startswith('eager-')
        if ('--no-capture' in argv) != eager:
            ap.error(f'{condition}: capture route mismatch')
        if ('--mtp' in argv) != bool(mtp):
            ap.error(f'{condition}: MTP artifact does not match factor')
        if '--adapt-accepted-only' not in argv or '--suffix-draft' not in argv:
            ap.error(f'{condition}: accepted-only/suffix-draft control mismatch')
    rng = random.Random(args.seed)
    schedule = []
    for block in range(args.blocks):
        order = list(CONDITIONS)
        rng.shuffle(order)
        schedule.extend({'block': block, 'condition': name, 'status': 'not_run'} for name in order)
    print(json.dumps({'seed': args.seed, 'blocks': args.blocks, 'schedule': schedule}, indent=2))
    if not args.run:
        return 0
    args.output.mkdir(parents=True, exist_ok=False)
    campaign = {
        'schema': 1,
        'design': 'three-block randomized screening; captured/eager × MTP off/window2',
        'seed': args.seed,
        'adaptation_policy': '--adapt-every 4 --adapt-accepted-only',
        'model': 'Qwen3.8-Flash-Next-GSQ-RCO-Q2_0 local Orin validation artifacts',
        'binary_sha256': subprocess.check_output(['sha256sum', str(ROOT / 'build/integration/candidate/strata')], text=True).split()[0],
        'workloads': str((HERE / 'workloads.json').resolve()),
        'warmup_workloads': str((HERE / 'warmup-workloads.json').resolve()),
        'configurations': {name: str(path.resolve()) for name, path in configs.items()},
        'started_wall_time_s': time.time(),
        'runs': schedule,
    }
    experiment = args.output / 'experiment.json'
    experiment.write_text(json.dumps(campaign, indent=2) + '\n')
    for index, row in enumerate(campaign['runs']):
        condition = row['condition']
        run_dir = args.output / f"block-{row['block']}-{condition}"
        run_dir.mkdir(parents=True)
        request_path = run_dir / 'requests.json'
        command = [sys.executable, str(RUN_CONTROL), '--output', str((run_dir / 'supervisor').resolve()),
                   '--timeout', '1800', '--interval', '1', '--sample-clocks', '--',
                   sys.executable, str(API_BLOCK), '--config', str(configs[condition].resolve()),
                   '--workloads', str((HERE / 'workloads.json').resolve()),
                   '--warmup-workloads', str((HERE / 'warmup-workloads.json').resolve()),
                   '--output', str(request_path.resolve()), '--variant',
                   'candidate' if condition.startswith('captured-') else 'baseline',
                   '--rounds', '1', '--no-trace']
        row.update(command=command, status='running', reason='incomplete until terminal supervisor result')
        experiment.write_text(json.dumps(campaign, indent=2) + '\n')
        print('starting', run_dir.name, flush=True)
        with (run_dir / 'driver-stdout.txt').open('w') as out:
            code = subprocess.call(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
        terminal_path = run_dir / 'supervisor/result.json'
        if terminal_path.exists():
            terminal = json.loads(terminal_path.read_text())
            row.update(status=terminal['status'], supervisor_returncode=code,
                       elapsed_s=terminal.get('elapsed_s'), reason=terminal.get('reason'),
                       minimum_available_bytes=terminal.get('minimum_available_bytes'),
                       minimum_admission_available_bytes=terminal.get('minimum_admission_available_bytes'))
        else:
            row.update(status='fail', supervisor_returncode=code, reason='missing terminal supervisor result')
        experiment.write_text(json.dumps(campaign, indent=2) + '\n')
        print('finished', run_dir.name, row['status'], flush=True)
        if row['status'] != 'pass' or code:
            for pending in campaign['runs'][index + 1:]:
                pending['reason'] = 'not launched after failed/aborted cell; investigate before resuming'
            experiment.write_text(json.dumps(campaign, indent=2) + '\n')
            return 1
    campaign['finished_wall_time_s'] = time.time()
    experiment.write_text(json.dumps(campaign, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
