"""Run randomized 2x2 Q2_0 cache/context accepted-state screen."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache-values', type=int, nargs='+', default=[3000, 5000])
    parser.add_argument('--context-values', type=int, nargs='+', default=[8192, 65536])
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--seed', type=int, default=202610126)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--python', type=Path, default=Path(sys.executable),
                        help='Python executable with the serving dependencies installed')
    args = parser.parse_args()
    if args.repetitions < 2 or args.timeout < 1:
        parser.error('at least two repetitions and a positive timeout are required')
    if not args.engine.is_file() or not args.config.is_file() or not args.python.is_file():
        parser.error('engine, config, and integration Python must exist')

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = json.loads(args.config.read_text())
    config = dict(base)
    config['env'] = dict(config.get('env', {}))
    config['env'].pop('LD_PRELOAD', None)
    clean_config = output / 'base-config.json'
    clean_config.write_text(json.dumps(config, indent=2) + '\n')

    cells = [(cache, context) for cache in args.cache_values for context in args.context_values]
    if len(set(cells)) != len(cells) or not cells:
        parser.error('cache/context cells must be unique and nonempty')
    order = []
    rng = random.Random(args.seed)
    for repetition in range(args.repetitions):
        batch = list(cells)
        rng.shuffle(batch)
        order.extend((repetition, cache, context) for cache, context in batch)
    manifest = {
        'schema': 1,
        'scope': 'randomized fresh-process correctness/admission matrix; fixed 511-token accepted prefix and one generated token',
        'seed': args.seed,
        'repetitions': args.repetitions,
        'cache_values': args.cache_values,
        'context_values': args.context_values,
        'engine': str(args.engine.resolve()),
        'engine_sha256': __import__('hashlib').sha256(args.engine.read_bytes()).hexdigest(),
        'floor_bytes': 6 * 1024**3,
        'runs': [],
    }
    (output / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
    tool_dir = ROOT / 'tools/integration'
    runner = Path(__file__).with_name('runner.py')
    for index, (repetition, cache, context) in enumerate(order):
        name = f'rep-{repetition:02d}-cache-{cache}-context-{context}'
        run_dir = output / 'runs' / name
        run_dir.mkdir(parents=True)
        row = {'name': name, 'repetition': repetition, 'order': index,
               'cache_budget': cache, 'context_tokens': context,
               'status': 'not_run', 'minimum_available_bytes': None}
        manifest['runs'].append(row)
        cell_config = run_dir / 'config.json'
        cell_config.write_text(json.dumps(config, indent=2) + '\n')
        command = [str(args.python.resolve()), str(tool_dir / 'run_control.py'),
                   '--sample-clocks', '--privileged-emc', '--output', str((run_dir / 'supervisor').resolve()),
                   '--timeout', str(args.timeout), '--', str(args.python.resolve()), str(runner.resolve()),
                   '--config', str(cell_config.resolve()), '--engine', str(args.engine.resolve()),
                   '--output', str(run_dir.resolve()), '--cache', str(cache), '--context', str(context)]
        row['command'] = command
        (output / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('starting', name, flush=True)
        with (run_dir / 'launch.log').open('w') as log:
            returncode = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        supervisor = run_dir / 'supervisor' / 'result.json'
        if supervisor.exists():
            result = json.loads(supervisor.read_text())
            row.update(status=result.get('status', 'fail'),
                       minimum_available_bytes=result.get('minimum_available_bytes'),
                       elapsed_s=result.get('elapsed_s'),
                       supervisor_returncode=returncode,
                       reason=result.get('reason'))
        else:
            row.update(status='fail', supervisor_returncode=returncode,
                       reason='missing supervisor result')
        if row['status'] == 'pass':
            owner_command = [str(VENV_PYTHON), str(tool_dir / 'owner_observations.py'),
                             '--engine-log', str((run_dir / 'engine.log').resolve()),
                             '--output', str((run_dir / 'owner-summary.json').resolve())]
            result = subprocess.run(owner_command, cwd=ROOT, capture_output=True, text=True)
            row['owner_summary_returncode'] = result.returncode
            if result.returncode:
                row['owner_summary_error'] = result.stderr
                row['status'] = 'fail'
            else:
                request = json.loads((run_dir / 'workload.json').read_text())
                row['prompt_sha256'] = request['prompt_sha256']
                row['generated_ids'] = request['generated_ids']
                row['gdn_dump_sha256'] = request['gdn_dump_sha256']
                row['gdn_dump_path'] = request['gdn_dump_path']
                row['engine_sha256'] = request['engine_sha256']
        (output / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('finished', name, row['status'], row.get('reason'), flush=True)
        if row['status'] != 'pass':
            for pending_rep, pending_cache, pending_context in order[index + 1:]:
                manifest['runs'].append({
                    'name': f'rep-{pending_rep:02d}-cache-{pending_cache}-context-{pending_context}',
                    'repetition': pending_rep, 'cache_budget': pending_cache,
                    'context_tokens': pending_context, 'status': 'not_run',
                    'reason': 'not launched after failed or pressure-aborted cell'})
            break
    manifest['finished_wall_time_s'] = time.time()
    (output / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return int(any(row['status'] != 'pass' for row in manifest['runs']))


if __name__ == '__main__':
    raise SystemExit(main())
