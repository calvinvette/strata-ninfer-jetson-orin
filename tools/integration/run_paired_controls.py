"""Sequential randomized same-day controls with independent owned processes."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys
import time

from run_control import write_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-config', type=Path, required=True)
    parser.add_argument('--candidate-config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--blocks', type=int, default=3)
    parser.add_argument('--seed', type=int, default=870126)
    parser.add_argument('--prior-campaign', type=Path, help='completed compatible campaign to extend with additional independent pairs')
    args = parser.parse_args()
    first_block = 0
    if args.prior_campaign:
        prior = json.loads((args.prior_campaign / 'campaign.json').read_text())
        if not prior.get('finished_wall_time_s') or any(r['status'] != 'pass' for r in prior['runs']):
            parser.error('prior campaign is not successfully terminal')
        first_block = max(row['block'] for row in prior['runs']) + 1
        for variant, config in [('baseline', args.baseline_config), ('candidate', args.candidate_config)]:
            row = next(r for r in prior['runs'] if r['variant'] == variant)
            old = json.loads((args.prior_campaign / f"block-{row['block']}-{variant}/server-config.json").read_text())
            new = json.loads(config.read_text())
            for key in ('args', 'tokenizer', 'draft_vocab', 'exe', 'cwd'):
                if old.get(key) != new.get(key):
                    parser.error(f'prior configuration mismatch: {variant} {key}')
    if args.blocks < 1 or args.blocks + first_block < 3:
        parser.error('at least three total independent paired screening blocks required')
    args.output.mkdir(parents=True, exist_ok=False)
    rng = random.Random(args.seed)
    workloads = json.loads(args.workloads.read_text())
    runs = []
    for block in range(first_block, first_block + args.blocks):
        variants = ['baseline', 'candidate']
        rng.shuffle(variants)
        ordered = dict(workloads)
        ordered['workloads'] = list(workloads['workloads'])
        rng.shuffle(ordered['workloads'])
        path = args.output / f'block-{block}-workloads.json'
        path.write_text(json.dumps(ordered, indent=2) + '\n')
        for variant in variants:
            runs.append({'block': block, 'variant': variant, 'status': 'not_run',
                         'workloads': str(path.resolve())})
    result = {'seed': args.seed, 'planned_blocks': args.blocks, 'runs': runs,
              'prior_campaign': str(args.prior_campaign.resolve()) if args.prior_campaign else None,
              'scope': 'independent processes; randomized order within same-day pairs; one warmup/cell/process',
              'started_wall_time_s': time.time()}
    output = args.output / 'campaign.json'
    write_result(output, result)
    directory = Path(__file__).resolve().parent
    for index, row in enumerate(runs):
        name = f"block-{row['block']}-{row['variant']}"
        run_dir = args.output / name
        config = args.baseline_config if row['variant'] == 'baseline' else args.candidate_config
        command = [sys.executable, str(directory / 'run_control.py'), '--output', str(run_dir.resolve()),
                   '--timeout', '1800', '--', sys.executable, str(directory / 'api_control_block.py'),
                   '--config', str(config.resolve()), '--workloads', row['workloads'],
                   '--output', str((run_dir / 'requests.json').resolve()), '--variant', row['variant']]
        row.update(command=command, reason='running; incomplete until supervisor terminal result')
        write_result(output, result)
        print('starting', name, flush=True)
        with (args.output / f'{name}-supervisor.txt').open('w') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        if (run_dir / 'result.json').exists():
            terminal = json.loads((run_dir / 'result.json').read_text())
            row.update(status=terminal['status'], reason=terminal.get('reason'),
                       supervisor_returncode=code, result=str((run_dir / 'result.json').resolve()))
        else:
            row.update(status='fail', reason='missing terminal supervisor record', supervisor_returncode=code)
        write_result(output, result)
        print('finished', name, row['status'], row['reason'], flush=True)
        if row['status'] != 'pass':
            for pending in runs[index + 1:]:
                pending['reason'] = 'not launched after failed/pressure-aborted block; investigate before resuming'
            write_result(output, result)
            return 1
    result['finished_wall_time_s'] = time.time()
    write_result(output, result)
    return int(any(row['status'] != 'pass' for row in runs))


if __name__ == '__main__':
    raise SystemExit(main())
