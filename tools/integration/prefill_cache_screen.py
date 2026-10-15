"""Run a randomized cache-budget × prefill-chunk screening block."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys
import time

from cache_context_screen import api_command, replace_option
from run_control import write_result


def prefill_cache_configs(config, cache_values, prefill_values):
    cells = []
    for cache in cache_values:
        for prefill in prefill_values:
            args = replace_option(config['args'], '--expert-cache', cache)
            args = replace_option(args, '--prefill', prefill)
            cfg = dict(config, args=args)
            cells.append({'name': f'cache{cache}-prefill{prefill}',
                          'expert_cache_argument': cache,
                          'prefill_chunk_tokens': prefill,
                          'config': cfg})
    return cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--warmup-workloads', type=Path,
                        help='optional distinct workload used only to warm each service')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache-values', type=int, nargs='+', default=[3000, 5000])
    parser.add_argument('--prefill-values', type=int, nargs='+', default=[32, 128])
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--seed', type=int, default=202610151)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--python', type=Path, default=Path(sys.executable),
                        help='Python executable with server dependencies installed')
    parser.add_argument('--no-trace', action='store_true',
                        help='disable STRATA_TRACE for request timing')
    parser.add_argument('--sample-clocks', action='store_true',
                        help='retain read-only CPU/GPU/EMC frequency samples per cell')
    parser.add_argument('--confirmation', action='store_true',
                        help='allow one measured request per independent cell/block')
    args = parser.parse_args()
    min_rounds = 1 if args.confirmation else 3
    if args.rounds < min_rounds or args.timeout < 1:
        parser.error(f'requires at least {min_rounds} measured rounds and a positive timeout')
    if (any(value <= 0 for value in args.cache_values + args.prefill_values)
            or len(set(args.cache_values)) != len(args.cache_values)
            or len(set(args.prefill_values)) != len(args.prefill_values)):
        parser.error('cache and prefill values must be positive and unique')
    config = json.loads(args.config.read_text())
    workloads = json.loads(args.workloads.read_text())
    if len(workloads.get('workloads', [])) != 1:
        parser.error('provide exactly one prepared workload per cell')
    cells = prefill_cache_configs(config, args.cache_values, args.prefill_values)
    rng = random.Random(args.seed)
    rng.shuffle(cells)
    args.output.mkdir(parents=True, exist_ok=False)
    campaign = {
        'seed': args.seed,
        'expert_cache_arguments': args.cache_values,
        'expert_cache_argument_units': 'equivalents of the largest expert blob',
        'prefill_chunk_tokens': args.prefill_values,
        'planned_cells': len(cells),
        'rounds_per_service': args.rounds,
        'trace_enabled': not args.no_trace,
        'clock_sampling': args.sample_clocks,
        'independent_block_confirmation': args.confirmation,
        'scope': 'randomized order; independent server process per cell; one warmup and three measured requests per process; admission and screening evidence only',
        'started_wall_time_s': time.time(),
        'cells': [],
    }
    manifest = args.output / 'campaign.json'
    write_result(manifest, campaign)
    tools = Path(__file__).resolve().parent
    for index, cell in enumerate(cells):
        name = cell['name']
        output = args.output / name
        output.mkdir()
        cfgpath = output / 'config.json'
        cfgpath.write_text(json.dumps(cell.pop('config'), indent=2) + '\n')
        request_path = output / 'requests.json'
        command = api_command(args.python.resolve(), tools, cfgpath, args.workloads,
                              request_path, args.rounds, timeout_s=args.timeout,
                              no_trace=args.no_trace, sample_clocks=args.sample_clocks,
                              warmup_workloads=args.warmup_workloads)
        row = dict(cell, order=index, status='not_run', command=command)
        campaign['cells'].append(row)
        write_result(manifest, campaign)
        print('starting', name, flush=True)
        with (output / 'supervisor.txt').open('w') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        terminal_path = output / 'supervisor' / 'result.json'
        if terminal_path.exists():
            terminal = json.loads(terminal_path.read_text())
            row.update(status=terminal['status'],
                       minimum_available_bytes=terminal.get('minimum_available_bytes'),
                       elapsed_s=terminal.get('elapsed_s'), reason=terminal.get('reason'),
                       supervisor_returncode=code)
        else:
            row.update(status='fail', reason='missing supervisor terminal record',
                       supervisor_returncode=code)
        if request_path.exists():
            requests = json.loads(request_path.read_text())
            row['request_summary'] = requests.get('summary')
            row['measured_samples'] = sum(sample.get('passed_samples', 0)
                                          for sample in requests.get('summary', []))
        write_result(manifest, campaign)
        print('finished', name, row['status'], row.get('reason'), flush=True)
        if row['status'] != 'pass':
            for pending in campaign['cells'][index + 1:]:
                pending.update(status='not_run',
                               reason='not launched after failed/pressure-aborted cell')
            write_result(manifest, campaign)
            return 1
    campaign['finished_wall_time_s'] = time.time()
    write_result(manifest, campaign)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
