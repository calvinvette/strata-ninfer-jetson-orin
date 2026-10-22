"""Run randomized cache-cap/context cells with three measured requests per process."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys
import time

from run_control import write_result


def replace_option(args, option, value):
    """Replace exactly one existing two-token CLI option; reject ambiguous configs."""
    positions = [i for i, item in enumerate(args) if item == option]
    if len(positions) != 1 or positions[0] + 1 >= len(args):
        raise ValueError(f'expected exactly one {option} option with a value')
    result = list(args)
    result[positions[0] + 1] = str(value)
    return result


def cell_configs(config, cache_values, context_values):
    cells = []
    for cache in cache_values:
        for context in context_values:
            cfg = dict(config)
            args = replace_option(config['args'], '--expert-cache', cache)
            cfg['args'] = replace_option(args, '--max-context', context)
            cells.append({'name': f'cache{cache}-ctx{context}',
                          'expert_cache_argument': cache,
                          'context_tokens': context, 'config': cfg})
    return cells


def api_command(runtime_python, tools, cfgpath, workloads, request_path, rounds,
                timeout_s=1800, no_trace=False, sample_clocks=False,
                warmup_workloads=None, scope_memory_gib=0):
    command = [str(runtime_python), str(tools / 'run_control.py'), '--output',
               str((request_path.parent / 'supervisor').resolve()), '--timeout', str(timeout_s)]
    if sample_clocks:
        command.append('--sample-clocks')
    command.extend(['--',
               str(runtime_python), str(tools / 'api_control_block.py'), '--config',
               str(cfgpath.resolve()), '--workloads', str(workloads.resolve()),
               '--output', str(request_path.resolve()), '--variant', 'candidate', '--rounds', str(rounds)])
    if warmup_workloads is not None:
        command.extend(['--warmup-workloads', str(warmup_workloads.resolve())])
    if no_trace:
        command.append('--no-trace')
    if scope_memory_gib:
        command = ['systemd-run', '--user', '--scope', '--collect',
                   '-p', f'MemoryMax={scope_memory_gib}G', '-p', 'IOAccounting=yes', *command]
    return command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache-values', type=int, nargs='+', default=[3000, 5000])
    parser.add_argument('--context-values', type=int, nargs='+', default=[4096, 8192])
    parser.add_argument('--rounds', type=int, default=3,
                        help='measured requests per cell (three for screening; one is valid for seven-block confirmation)')
    parser.add_argument('--confirmation', action='store_true',
                        help='allow one measured request per independent block')
    parser.add_argument('--seed', type=int, default=20261011)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--python', type=Path, default=Path(sys.executable),
                        help='Python executable with the server dependencies installed')
    parser.add_argument('--no-trace', action='store_true',
                        help='disable STRATA_TRACE for request timing')
    parser.add_argument('--sample-clocks', action='store_true',
                        help='record read-only CPU/GPU/EMC clock observations')
    parser.add_argument('--scope-memory-gib', type=int, default=0,
                        help='run every independent cell in its own systemd MemoryMax scope')
    args = parser.parse_args()
    if args.rounds < (1 if args.confirmation else 3) or args.timeout < 1:
        parser.error('screening requires three rounds; confirmation requires one; timeout must be positive')
    if args.scope_memory_gib < 0:
        parser.error('--scope-memory-gib must be zero or positive')
    if len(set(args.cache_values)) != len(args.cache_values) or len(set(args.context_values)) != len(args.context_values):
        parser.error('cache and context values must be unique')
    base = json.loads(args.config.read_text())
    workloads = json.loads(args.workloads.read_text())
    if not workloads.get('workloads'):
        parser.error('workload file must contain at least one prepared workload')
    cells = cell_configs(base, args.cache_values, args.context_values)
    rng = random.Random(args.seed)
    rng.shuffle(cells)
    args.output.mkdir(parents=True, exist_ok=False)
    campaign = {'seed': args.seed, 'cache_values': args.cache_values,
                'context_values': args.context_values, 'planned_cells': len(cells),
                'rounds_per_cell': args.rounds,
                'trace_enabled': not args.no_trace,
                'scope': ('seven-block confirmation; randomized order; independent server process per cell; '
                          'one warmup and one or more measured requests per process' if args.confirmation else
                          'randomized order; independent server process per cell; one warmup and three or more measured requests per process; admission and screening evidence only'),
                'started_wall_time_s': time.time(), 'cells': []}
    manifest = args.output / 'campaign.json'
    write_result(manifest, campaign)
    tools = Path(__file__).resolve().parent
    for index, cell in enumerate(cells):
        name = cell['name']
        out = args.output / name
        out.mkdir()
        cfgpath = out / 'config.json'
        cfgpath.write_text(json.dumps(cell.pop('config'), indent=2) + '\n')
        request_path = out / 'requests.json'
        runtime_python = str(args.python.resolve())
        command = api_command(args.python.resolve(), tools, cfgpath, args.workloads,
                              request_path, args.rounds, timeout_s=args.timeout,
                              no_trace=args.no_trace, sample_clocks=args.sample_clocks,
                              scope_memory_gib=args.scope_memory_gib)
        row = dict(cell, order=index, status='not_run', command=command)
        campaign['cells'].append(row)
        write_result(manifest, campaign)
        print('starting', name, flush=True)
        with (out / 'supervisor.txt').open('w') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        terminal_path = out / 'supervisor' / 'result.json'
        if terminal_path.exists():
            terminal = json.loads(terminal_path.read_text())
            row.update(status=terminal['status'], minimum_available_bytes=terminal.get('minimum_available_bytes'),
                       elapsed_s=terminal.get('elapsed_s'), reason=terminal.get('reason'),
                       supervisor_returncode=code)
        else:
            row.update(status='fail', reason='missing supervisor terminal record', supervisor_returncode=code)
        if request_path.exists():
            measured = json.loads(request_path.read_text())
            row['request_summary'] = measured.get('summary')
            row['measured_samples'] = sum(s.get('passed_samples', 0) for s in measured.get('summary', []))
        write_result(manifest, campaign)
        print('finished', name, row['status'], row.get('reason'), flush=True)
        if row['status'] != 'pass':
            for pending in campaign['cells'][index + 1:]:
                pending['status'] = 'not_run'
                pending['reason'] = 'not launched after failed/pressure-aborted cell'
            write_result(manifest, campaign)
            return 1
    campaign['finished_wall_time_s'] = time.time()
    write_result(manifest, campaign)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
