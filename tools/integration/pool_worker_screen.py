"""Randomized fixed-workload screen for Strata's CPU expert-pool worker count."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from prepare_controls import load_tokenizer
from serve.frontend import ChatTemplate

API_BLOCK = ROOT / 'tools/integration/api_control_block.py'


def set_arg(args, key, value):
    if key in args:
        args[args.index(key) + 1] = str(value)
    else:
        args.extend([key, str(value)])


def exact_warmup_prompt(target, encode, filler='blue '):
    prefix = 'Warmup context: '
    suffix = '\nWrite at least 200 words explaining how a computer processes information. Start with the processor.'
    low, high = 0, target
    while low <= high:
        count = (low + high) // 2
        text = prefix + filler * count + suffix
        actual = len(encode(text))
        if actual == target:
            return text
        if actual < target:
            low = count + 1
        else:
            high = count - 1
    raise ValueError(f'cannot construct a distinct warmup of exactly {target} tokens')


def make_warmup_workloads(workloads, tokenizer_path):
    tokenizer_path = Path(tokenizer_path)
    tokenizer = load_tokenizer(tokenizer_path)
    template_path = tokenizer_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')

    def encode(text):
        rendered = template.render([{'role': 'user', 'content': text}], enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    warmups = []
    for workload in workloads:
        row = dict(workload)
        row['messages'] = list(workload['messages'])
        if len(row['messages']) != 1 or row['messages'][0].get('role') != 'user':
            raise ValueError('distinct warmup generation expects one user message per workload')
        row['messages'][0] = dict(row['messages'][0])
        row['messages'][0]['content'] = exact_warmup_prompt(workload['prompt_tokens'], encode)
        row['warmup_prompt_tokens'] = len(encode(row['messages'][0]['content']))
        if row['warmup_prompt_tokens'] != workload['prompt_tokens']:
            raise ValueError('warmup prompt does not match the measured token count')
        warmups.append(row)
    return warmups


def read_state_hashes(log_path):
    keys = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
    result = []
    for line in log_path.read_text(errors='replace').splitlines():
        if 'STATE_HASH L=' not in line:
            continue
        fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
        if not set(keys) <= fields.keys():
            raise ValueError(f'incomplete persistent-state fingerprint in {log_path}')
        result.append({key: fields[key] for key in keys})
    return result


def read_accepted_prefix_trace(log_path):
    """Read the final measured request's token IDs and state at each verifier commit."""
    keys = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'mtp', 'stale', 'ple_prev')
    groups, current = [], []
    pattern = re.compile(r'ACCEPTED_PREFIX position=(\d+) window=(\d+) accepted_drafts=(\d+) '
                         r'committed=(\d+) tokens=([0-9,]+) state=\{STATE_HASH (.+)\}')
    for line in log_path.read_text(errors='replace').splitlines():
        if 'ACCEPTED_PREFIX ' in line:
            match = pattern.search(line)
            if not match:
                raise ValueError(f'malformed accepted-prefix trace in {log_path}: {line.strip()}')
            position, window, accepted, committed = map(int, match.group(1, 2, 3, 4))
            token_ids = [int(value) for value in match.group(5).split(',')]
            state = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', match.group(6)))
            if not set(keys) <= state.keys() or committed != len(token_ids) or committed < 1:
                raise ValueError(f'incomplete accepted-prefix trace in {log_path}: {line.strip()}')
            current.append({'position': position, 'window': window, 'accepted_drafts': accepted,
                            'committed': committed, 'token_ids': token_ids,
                            'state': {key: state[key] for key in keys}})
        elif 'strata serve: STATE_HASH L=' in line and current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    if not groups:
        return []
    # api_control_block always sends warmup first and the measured request last.
    return groups[-1]


def measured_request(path):
    data = json.loads(path.read_text())
    good = [row for row in data['checks'] if row['status'] == 'pass' and not row['warmup']]
    if len(good) != 1:
        raise ValueError(f'expected one passing measured request in {path}, got {len(good)}')
    row = good[0]
    timings = row['response'].get('timings', {})
    content = row['response']['choices'][0]['message'].get('content', '')
    return {
        'cell': row['cell'], 'prompt_tokens': row['response']['usage']['prompt_tokens'],
        'generated_tokens': row['response']['usage']['completion_tokens'],
        'prompt_ms': timings['prompt_ms'], 'decode_ms': timings['predicted_ms'],
        'request_ms': timings['prompt_ms'] + timings['predicted_ms'],
        'ttft_ms': row['stream_observation']['first_visible_delta_s'] * 1000,
        'output_sha256': hashlib.sha256(content.encode()).hexdigest(),
    }


def paired_deltas(rows, baseline):
    by_worker_rep = {(row['workers'], row['repetition']): row for row in rows}
    deltas = {}
    for workers in sorted({row['workers'] for row in rows} - {baseline}):
        values = []
        for repetition in sorted({row['repetition'] for row in rows}):
            base = by_worker_rep[baseline, repetition]['request_ms']
            candidate = by_worker_rep[workers, repetition]['request_ms']
            values.append((candidate - base) / base * 100.0)
        deltas[str(workers)] = values
    return deltas


def worker_transfer_effects(rows, baseline_workers, transfer_modes):
    """Return paired worker, transfer and difference-in-differences effects."""
    by_cell = {(row['repetition'], row['workers'], row['transfer_mode']): row
               for row in rows}
    repetitions = sorted({row['repetition'] for row in rows})
    effects = {'worker_delta_percent_by_mode': {},
               'pread_delta_percent_by_workers': {},
               'interaction_percentage_points': []}
    if 'mapped' not in transfer_modes or 'pread' not in transfer_modes:
        return effects
    workers = sorted({row['workers'] for row in rows})
    for mode in transfer_modes:
        effects['worker_delta_percent_by_mode'][mode] = {
            str(worker): [
                100.0 * (by_cell[rep, worker, mode]['request_ms'] /
                         by_cell[rep, baseline_workers, mode]['request_ms'] - 1.0)
                for rep in repetitions]
            for worker in workers if worker != baseline_workers
        }
    for worker in workers:
        effects['pread_delta_percent_by_workers'][str(worker)] = [
            100.0 * (by_cell[rep, worker, 'pread']['request_ms'] /
                     by_cell[rep, worker, 'mapped']['request_ms'] - 1.0)
            for rep in repetitions]
    if baseline_workers in workers and len(workers) > 1:
        candidate_workers = [w for w in workers if w != baseline_workers]
        if len(candidate_workers) == 1:
            candidate = str(candidate_workers[0])
            effects['interaction_percentage_points'] = [
                low - high for low, high in zip(
                    effects['pread_delta_percent_by_workers'][candidate],
                    effects['pread_delta_percent_by_workers'][str(baseline_workers)])]
    return effects


def bootstrap_median(values, seed, draws=200_000):
    rng = random.Random(seed)
    samples = sorted(statistics.median(values[rng.randrange(len(values))] for _ in values)
                     for _ in range(draws))
    return [samples[int(draws * 0.025)], samples[int(draws * 0.975)]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, nargs='+', default=[1, 2, 4, 8, 11])
    parser.add_argument('--transfer-modes', choices=('mapped', 'pread'), nargs='+',
                        default=['mapped'],
                        help='randomized file-tier read policies; use both for a 2x2 interaction screen')
    parser.add_argument('--io-threads', type=int, default=8,
                        help='pread worker count when --transfer-modes includes pread')
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--baseline-workers', type=int, default=11)
    parser.add_argument('--timing-only', action='store_true',
                        help='disable tracing; check API output/cache but not accepted-prefix state')
    args = parser.parse_args()
    if (args.repetitions < 2 or len(set(args.workers)) != len(args.workers) or
            any(n < 1 for n in args.workers) or args.io_threads < 1 or
            len(set(args.transfer_modes)) != len(args.transfer_modes)):
        parser.error('workers/modes must be unique, worker counts and I/O threads positive, and repetitions at least two')
    if args.baseline_workers not in args.workers:
        parser.error('baseline worker count must be in --workers')
    if args.output.exists():
        parser.error('output directory already exists')
    cfg = json.loads(args.config.read_text())
    if not cfg.get('args') or not cfg.get('exe'):
        parser.error('config must identify a Strata executable and argument list')

    args.output.mkdir(parents=True, exist_ok=False)
    runs = args.output / 'runs'
    runs.mkdir()
    workloads = json.loads(args.workloads.read_text())['workloads']
    warmup_workloads = make_warmup_workloads(workloads, cfg['tokenizer'])
    warmup_path = args.output / 'warmup-workloads.json'
    warmup_path.write_text(json.dumps({'workloads': warmup_workloads}, indent=2) + '\n')
    rng = random.Random(args.seed)
    result = {
        'scope': 'randomized process-block screen; one fixed real-model API workload per process after a warmup',
        'correctness_mode': 'API output/cache only; tracing disabled' if args.timing_only else
                            'full accepted-prefix state and output; tracing enabled',
        'seed': args.seed, 'planned_repetitions': args.repetitions,
        'workers': sorted(args.workers), 'transfer_modes': list(args.transfer_modes),
        'io_threads': args.io_threads, 'baseline_workers': args.baseline_workers,
        'engine_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
        'runs': [], 'failures': [],
    }
    base_port = int(cfg['port'])
    for repetition in range(args.repetitions):
        order = [(workers, mode) for workers in args.workers for mode in args.transfer_modes]
        rng.shuffle(order)
        for cell_index, (workers, transfer_mode) in enumerate(order):
            run_dir = runs / f'rep-{repetition:02d}-workers-{workers}-{transfer_mode}'
            run_dir.mkdir()
            run_cfg = dict(cfg)
            run_cfg['args'] = list(cfg['args'])
            set_arg(run_cfg['args'], '--pool-workers', workers)
            set_arg(run_cfg['args'], '--prompt-cache', 6)
            run_cfg['port'] = base_port + repetition * len(args.workers) * len(args.transfer_modes) + cell_index
            run_cfg['log'] = str((run_dir / 'engine.log').resolve())
            run_cfg['env'] = dict(cfg.get('env', {}))
            run_cfg['env'].update({
                'STRATA_IO_PREFETCH': '1' if transfer_mode == 'pread' else '0',
                'STRATA_IO_PF_THREADS': str(args.io_threads),
                'STRATA_IO_PF_STAGE': '0',
            })
            if args.timing_only:
                for key in ('STRATA_TRACE', 'STRATA_STATE_HASH', 'STRATA_STATE_HASH_GDN',
                            'STRATA_INTEGRATION_TRACE', 'STRATA_ACCEPTED_PREFIX_TRACE'):
                    run_cfg['env'].pop(key, None)
            else:
                run_cfg['env'].update({'STRATA_TRACE': '1', 'STRATA_STATE_HASH': '1',
                                       'STRATA_INTEGRATION_TRACE': '1',
                                       'STRATA_ACCEPTED_PREFIX_TRACE': '1'})
            config_path = run_dir / 'server-config.json'
            config_path.write_text(json.dumps(run_cfg, indent=2) + '\n')
            request_path = run_dir / 'requests.json'
            command = [sys.executable, str(API_BLOCK), '--config', str(config_path),
                       '--workloads', str(args.workloads.resolve()), '--output', str(request_path),
                       '--warmup-workloads', str(warmup_path.resolve()),
                       '--variant', 'candidate', '--rounds', '1']
            if args.timing_only:
                command.append('--no-trace')
            with (run_dir / 'launcher.log').open('w') as log:
                completed = subprocess.run(command, cwd=cfg.get('cwd', str(ROOT)),
                                           stdout=log, stderr=subprocess.STDOUT,
                                           timeout=900, check=False)
            row = {'repetition': repetition, 'workers': workers, 'transfer_mode': transfer_mode,
                   'order': [[count, mode] for count, mode in order], 'cell_order': cell_index,
                   'returncode': completed.returncode, 'request_file': str(request_path.relative_to(args.output))}
            try:
                if completed.returncode != 0:
                    raise RuntimeError(f'API block exited {completed.returncode}')
                row.update(measured_request(request_path))
                log_path = run_dir / 'engine.log'
                text = log_path.read_text(errors='replace')
                slot_counts = {int(n) for n in re.findall(r'expert cache (\d+) slots', text)}
                row['actual_expert_cache_slots'] = next(iter(slot_counts)) if len(slot_counts) == 1 else None
                if not args.timing_only:
                    row['state_hashes'] = read_state_hashes(log_path)
                    row['accepted_prefix_trace'] = read_accepted_prefix_trace(log_path)
                    if not row['state_hashes']:
                        raise ValueError(f'missing state fingerprints in {log_path}')
                    if not row['accepted_prefix_trace']:
                        raise ValueError(f'missing accepted-prefix trace in {log_path}')
                    if sum(len(trace['token_ids']) for trace in row['accepted_prefix_trace']) != row['generated_tokens']:
                        raise ValueError(f'accepted-prefix trace does not cover every generated token in {log_path}')
                if row['actual_expert_cache_slots'] is None:
                    raise ValueError(f'cache capacity missing or conflicting in {log_path}')
            except (OSError, KeyError, ValueError, RuntimeError) as exc:
                row['failure'] = f'{type(exc).__name__}: {exc}'
                result['failures'].append({'repetition': repetition, 'workers': workers,
                                           'failure': row['failure']})
            result['runs'].append(row)
            (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')

    valid = [row for row in result['runs'] if 'failure' not in row]
    if len(valid) != args.repetitions * len(args.workers) * len(args.transfer_modes):
        result['passed'] = False
    else:
        slots = {row['actual_expert_cache_slots'] for row in valid}
        result['actual_cache_slots_equal'] = len(slots) == 1
        result['measured_output_equal'] = len({row['output_sha256'] for row in valid}) == 1
        if not args.timing_only:
            state = [row['state_hashes'][-1] for row in valid]
            result['measured_state_equal'] = len({json.dumps(row, sort_keys=True) for row in state}) == 1
            result['measured_accepted_prefix_equal'] = len({json.dumps(row['accepted_prefix_trace'], sort_keys=True)
                                                            for row in valid}) == 1
        if len(args.transfer_modes) == 1:
            result['paired_request_time_delta_percent'] = paired_deltas(valid, args.baseline_workers)
            result['bootstrap_95pct_median_intervals_percent'] = {
                worker: bootstrap_median(values, args.seed + int(worker))
                for worker, values in result['paired_request_time_delta_percent'].items()}
        else:
            result['factorial_effects'] = worker_transfer_effects(
                valid, args.baseline_workers, args.transfer_modes)
            effects = result['factorial_effects']
            result['factorial_effects']['bootstrap_95pct_median_intervals'] = {
                'worker_delta_percent_by_mode': {
                    mode: {worker: bootstrap_median(values, args.seed + int(worker) +
                                                    (0 if mode == 'mapped' else 1000))
                           for worker, values in workers.items()}
                    for mode, workers in effects['worker_delta_percent_by_mode'].items()},
                'pread_delta_percent_by_workers': {
                    worker: bootstrap_median(values, args.seed + int(worker) + 2000)
                    for worker, values in effects['pread_delta_percent_by_workers'].items()},
                'interaction_percentage_points': bootstrap_median(
                    effects['interaction_percentage_points'], args.seed + 3000)
                    if effects['interaction_percentage_points'] else None,
            }
        result['summary'] = {}
        for workers in sorted(args.workers):
            by_mode = {}
            for mode in args.transfer_modes:
                selected = [row for row in valid if row['workers'] == workers and
                            row['transfer_mode'] == mode]
                by_mode[mode] = {
                    'samples': len(selected),
                    'median_prompt_ms': statistics.median(row['prompt_ms'] for row in selected),
                    'median_decode_ms': statistics.median(row['decode_ms'] for row in selected),
                    'median_ttft_ms': statistics.median(row['ttft_ms'] for row in selected),
                    'median_request_ms': statistics.median(row['request_ms'] for row in selected),
                    'output_hashes': sorted({row['output_sha256'] for row in selected}),
                }
            result['summary'][str(workers)] = by_mode[args.transfer_modes[0]] if len(args.transfer_modes) == 1 else by_mode
        result['passed'] = (result['actual_cache_slots_equal'] and result['measured_output_equal'] and
                            (args.timing_only or (result['measured_state_equal'] and
                                                  result['measured_accepted_prefix_equal'])) and
                            not result['failures'])
        if not result['actual_cache_slots_equal']:
            result['failures'].append({'failure': 'actual expert-cache capacity differs across cells'})
        if not args.timing_only and not result['measured_state_equal']:
            result['failures'].append({'failure': 'measured persistent-state fingerprints differ across cells'})
        if not result['measured_output_equal']:
            result['failures'].append({'failure': 'measured output content differs across worker counts'})
        if not args.timing_only and not result['measured_accepted_prefix_equal']:
            result['failures'].append({'failure': 'accepted token IDs or committed state differ at a verifier boundary'})
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result.get(key) for key in
          ('passed', 'failures', 'summary', 'measured_accepted_prefix_equal', 'paired_request_time_delta_percent',
           'bootstrap_95pct_median_intervals_percent', 'factorial_effects')}, indent=2))
    return 0 if result.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
