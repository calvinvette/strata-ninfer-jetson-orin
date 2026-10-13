#!/usr/bin/env python3
"""Run a randomized seven-block held-out Q6_K warp-dequant × MTP Orin confirmation in blocks."""
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
CONDITIONS = ('baseline-mtp0', 'warp-mtp0', 'baseline-mtp4', 'warp-mtp4')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True, help='new output directory')
    ap.add_argument('--blocks', type=int, default=3)
    ap.add_argument('--seed', type=int, default=202610124)
    ap.add_argument('--config-dir', type=Path,
                    help='optional directory containing the four condition configs')
    ap.add_argument('--accepted-only', action='store_true',
                    help='derive per-cell configs with accepted-token adaptation enabled')
    ap.add_argument('--run', action='store_true', help='execute; otherwise print the randomized design')
    args = ap.parse_args()
    if args.blocks < 3 or args.output.exists():
        ap.error('screening needs at least 3 blocks and a new output path')
    if args.run:
        args.output.mkdir(parents=True, exist_ok=False)
    configs = {}
    for condition in CONDITIONS:
        label, mtp = condition.split('-mtp')
        path = ((args.config_dir or HERE) / f'{label}-mtp{mtp}-config.json')
        cfg = json.loads(path.read_text())
        argv = cfg['args']
        actual_mtp = int(argv[argv.index('--spec') + 1])
        if actual_mtp != max(2, int(mtp)):
            ap.error(f'{path}: unexpected --spec value {actual_mtp}')
        has_mtp = '--mtp' in argv
        if has_mtp != (mtp == '4'):
            ap.error(f'{path}: MTP artifact path does not match factor level')
        if ('STRATA_Q6K_WARP_DEQUANT' in cfg.get('env', {})) != (label == 'warp'):
            ap.error(f'{path}: warp environment does not match factor level')
        if '--suffix-draft' not in argv or argv[argv.index('--suffix-draft') + 1] != '0':
            ap.error(f'{path}: suffix drafting must be disabled in all four cells')
        if args.accepted_only:
            if '--adapt-accepted-only' in argv:
                ap.error(f'{path}: accepted-only flag already present')
            argv.extend(['--adapt-every', '4', '--adapt-accepted-only'])
            derived = args.output / 'configs' / path.name
            derived.parent.mkdir(parents=True, exist_ok=True)
            derived.write_text(json.dumps(cfg, indent=2) + '\n')
            path = derived
        configs[condition] = path
    rng = random.Random(args.seed)
    schedule = []
    for block in range(args.blocks):
        order = list(CONDITIONS)
        rng.shuffle(order)
        schedule.extend({'block': block, 'condition': condition} for condition in order)
    print(json.dumps({'seed': args.seed, 'blocks': args.blocks, 'schedule': schedule}, indent=2))
    if not args.run:
        return 0
    campaign = {'schema': 1, 'design': 'randomized confirmation; held-out prompt; Q6_K warp-dequant (off/on) × MTP (off/window4)',
                'seed': args.seed, 'planned_blocks': args.blocks, 'started_wall_time_s': time.time(),
                'adaptation_policy': 'accepted-only, --adapt-every 4' if args.accepted_only else 'configuration-defined',
                'configurations': {k: str(v.resolve()) for k, v in configs.items()},
                'workloads': str((HERE / 'workloads.json').resolve()),
                'warmup_workloads': str((HERE / 'warmup-workloads.json').resolve()),
                'runs': [{**row, 'status': 'not_run'} for row in schedule]}
    path = args.output / 'experiment.json'
    path.write_text(json.dumps(campaign, indent=2) + '\n')
    for index, row in enumerate(campaign['runs']):
        condition = row['condition']
        label, mtp = condition.split('-mtp')
        run_dir = args.output / f"block-{row['block']}-{condition}"
        cfg = configs[condition]
        argv = [sys.executable, str(RUN_CONTROL), '--output', str((run_dir / 'supervisor').resolve()),
                '--timeout', '1800', '--interval', '1', '--sample-clocks', '--',
                sys.executable, str(API_BLOCK), '--config', str(cfg.resolve()),
                '--workloads', str((HERE / 'workloads.json').resolve()),
                '--warmup-workloads', str((HERE / 'warmup-workloads.json').resolve()),
                '--output', str((run_dir / 'requests.json').resolve()),
                '--variant', 'baseline' if label == 'baseline' else 'candidate', '--rounds', '1', '--no-trace']
        row.update(command=argv, status='running', reason='incomplete until terminal supervisor result')
        path.write_text(json.dumps(campaign, indent=2) + '\n')
        print('starting', run_dir.name, flush=True)
        run_dir.mkdir(parents=True)
        with (run_dir / 'driver-stdout.txt').open('w') as out:
            code = subprocess.call(argv, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
        terminal_path = run_dir / 'supervisor/result.json'
        if terminal_path.exists():
            terminal = json.loads(terminal_path.read_text())
            row.update(status=terminal['status'], supervisor_returncode=code,
                       elapsed_s=terminal.get('elapsed_s'), reason=terminal.get('reason'))
        else:
            row.update(status='fail', supervisor_returncode=code, reason='missing terminal supervisor result')
        path.write_text(json.dumps(campaign, indent=2) + '\n')
        print('finished', run_dir.name, row['status'], flush=True)
        if row['status'] != 'pass' or code:
            for pending in campaign['runs'][index + 1:]:
                pending['reason'] = 'not launched after failed/aborted cell; investigate before resuming'
            path.write_text(json.dumps(campaign, indent=2) + '\n')
            return 1
    campaign['finished_wall_time_s'] = time.time()
    path.write_text(json.dumps(campaign, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
