"""Randomized, no-trace paired request screen for native MTP windows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import args_for
from run_control import write_result
from summarize_controls import interval, measured, metrics


def canonical_args(args):
    """Remove only MTP window selection when checking paired configurations."""
    result = []
    i = 0
    while i < len(args):
        if args[i] in ('--mtp', '--mtp-max-t', '--spec'):
            i += 2
        else:
            result.append(args[i])
            i += 1
    return result


def one_measured(path):
    data = json.loads(path.read_text())
    rows = [row for row in data['checks'] if not row.get('warmup')]
    if len(rows) != 1:
        raise ValueError(f'expected exactly one measured API request, found {len(rows)}')
    return rows[0]


def select_workload(workload_data, cell=None):
    rows = workload_data.get('workloads', [])
    if cell is not None:
        rows = [row for row in rows if row.get('cell') == cell]
    if len(rows) != 1:
        raise ValueError(f'expected exactly one selected workload, found {len(rows)}')
    return rows[0]


def validate_mtp_arm_args(args, window):
    has_weights = '--mtp' in args
    if window == 0:
        if has_weights:
            raise ValueError('MTP-off arm still has draft weights configured')
        return
    if not has_weights:
        raise ValueError(f'MTP window {window} has no --mtp draft weights configured')
    path = Path(args[args.index('--mtp') + 1])
    if not path.exists():
        raise ValueError(f'MTP draft weights do not exist: {path}')
    if '--mtp-max-t' not in args or int(args[args.index('--mtp-max-t') + 1]) != window:
        raise ValueError(f'MTP window {window} does not match --mtp-max-t')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--workload-cell',
                        help='select one named workload from a multi-cell workload file')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--windows', type=int, nargs='+', default=[0, 2, 3, 4])
    parser.add_argument('--blocks', type=int, default=3)
    parser.add_argument('--seed', type=int, default=20261011)
    parser.add_argument('--first-port', type=int, default=18480)
    args = parser.parse_args()
    if args.blocks < 3 or len(args.windows) < 2 or args.windows[0] != 0 or len(set(args.windows)) != len(args.windows):
        parser.error('use at least 3 blocks and unique windows beginning with 0')
    if any(window < 0 or window > 4 for window in args.windows):
        parser.error('supported window screen is limited to 0..4')
    if args.output.exists():
        parser.error('output path already exists')
    cfg = json.loads(args.config.read_text())
    workload_data = json.loads(args.workloads.read_text())
    try:
        selected_workload = select_workload(workload_data, args.workload_cell)
    except ValueError as exc:
        parser.error(str(exc))
    arm_args_by_window = {}
    try:
        for window in args.windows:
            arm_args = args_for(cfg, window)
            validate_mtp_arm_args(arm_args, window)
            arm_args_by_window[window] = arm_args
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True)
    selected_data = dict(workload_data)
    selected_data['workloads'] = [selected_workload]
    selected_workloads_path = args.output / 'selected-workloads.json'
    selected_workloads_path.write_text(json.dumps(selected_data, indent=2) + '\n')
    rng = random.Random(args.seed)
    campaign = {'schema': 1, 'source_config': str(args.config.resolve()),
                'workloads': str(args.workloads.resolve()), 'windows': args.windows,
                'selected_workload': selected_workload.get('cell'),
                'blocks': args.blocks, 'seed': args.seed,
                'scope': 'one warmup and one measured request in each fresh process; randomized windows within blocks; no trace',
                'started_wall_time_s': time.time(), 'runs': [], 'comparisons': []}
    path = args.output / 'campaign.json'
    write_result(path, campaign)
    script_dir = Path(__file__).resolve().parent
    base_env = dict(cfg.get('env', {}))
    # The execution adapter explicitly disables trace/hash instrumentation.
    for key in ('STRATA_TRACE', 'STRATA_STATE_HASH', 'STRATA_STATE_HASH_GDN',
                'STRATA_INTEGRATION_TRACE', 'STRATA_ACCEPTED_PREFIX_TRACE'):
        base_env.pop(key, None)
    base_env['STRATA_PREFILL_CPU_SHARE'] = '0'

    for block in range(args.blocks):
        ordered = list(args.windows)
        rng.shuffle(ordered)
        for window in ordered:
            run_dir = args.output / f'block-{block:02d}-window-{window}'
            run_dir.mkdir()
            arm_args = list(arm_args_by_window[window])
            arm_args[arm_args.index('--prompt-cache') + 1] = '0'
            run_cfg = dict(cfg)
            run_cfg.update(args=arm_args, env=base_env, port=args.first_port + block * len(args.windows) + window,
                           log=str((run_dir / 'engine.log').resolve()))
            config_path = run_dir / 'server-config.json'
            config_path.write_text(json.dumps(run_cfg, indent=2) + '\n')
            request_path = run_dir / 'requests.json'
            command = [sys.executable, str(script_dir / 'run_control.py'), '--output',
                       str((run_dir / 'supervisor').resolve()), '--timeout', '1800', '--',
                       sys.executable, str(script_dir / 'api_control_block.py'), '--config',
                       str(config_path.resolve()), '--workloads', str(selected_workloads_path.resolve()),
                       '--output', str(request_path.resolve()), '--variant', 'candidate',
                       '--rounds', '1', '--no-trace']
            row = {'block': block, 'window': window, 'name': 'mtp-off' if window == 0 else f'mtp-window{window}',
                   'directory': str(run_dir.resolve()), 'status': 'not_run', 'command': command}
            campaign['runs'].append(row)
            write_result(path, campaign)
            print(f'starting block {block} window {window}', flush=True)
            with (run_dir / 'launch.txt').open('w') as log:
                launch_rc = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
            result_path = run_dir / 'supervisor' / 'result.json'
            if result_path.exists():
                sup = json.loads(result_path.read_text())
                row.update(status=sup['status'], supervisor_returncode=launch_rc,
                           minimum_available_bytes=sup.get('minimum_available_bytes'),
                           elapsed_s=sup.get('elapsed_s'), reason=sup.get('reason'))
                if sup['status'] == 'pass' and request_path.exists():
                    try:
                        request = one_measured(request_path)
                        row.update(request_status=request['status'], request_reason=request['reason'])
                        if request['status'] == 'pass':
                            row['metrics'] = metrics(request)
                            row['api_content'] = request['response']['choices'][0]['message']
                            row['engine'] = request['metrics_after']['engine']
                    except (KeyError, ValueError, OSError) as exc:
                        row.update(status='fail', reason=f'invalid request record: {exc}')
                if launch_rc != 0:
                    row.update(status='fail', reason=f'run_control wrapper exited {launch_rc}')
            else:
                row.update(status='fail', supervisor_returncode=launch_rc,
                           reason='missing terminal supervisor result')
            write_result(path, campaign)
            print(f'finished block {block} window {window}: {row["status"]}', flush=True)
            if row['status'] != 'pass' or row.get('request_status') != 'pass':
                campaign['finished_wall_time_s'] = time.time()
                write_result(path, campaign)
                return 1

    controls = {}
    for row in campaign['runs']:
        controls.setdefault(row['block'], {})[row['window']] = row
    comparisons = []
    for window in args.windows[1:]:
        paired = []
        failures = []
        for block in range(args.blocks):
            off, candidate = controls[block][0], controls[block][window]
            off_cfg = json.loads((Path(off['directory']) / 'server-config.json').read_text())
            candidate_cfg = json.loads((Path(candidate['directory']) / 'server-config.json').read_text())
            if canonical_args(off_cfg['args']) != canonical_args(candidate_cfg['args']):
                failures.append(f'block {block}: non-MTP arguments differ')
                continue
            for key in ('tokenizer', 'model_name', 'draft_vocab', 'env', 'exe', 'cwd'):
                if off_cfg.get(key) != candidate_cfg.get(key):
                    failures.append(f'block {block}: paired {key} differs')
            if off['engine'].get('expert_slots') != candidate['engine'].get('expert_slots') or off['engine'].get('kv') != candidate['engine'].get('kv'):
                failures.append(f'block {block}: actual expert residency or KV format differs')
            if off['api_content'] != candidate['api_content']:
                failures.append(f'block {block}: generated API content differs')
            a, b = off['metrics'], candidate['metrics']
            paired.append({'block': block, 'mtp_off': a, 'candidate': b,
                           'decode_tps_delta_percent': (b['decode_tps'] / a['decode_tps'] - 1) * 100,
                           'ttft_delta_percent': (b['client_ttft_s'] / a['client_ttft_s'] - 1) * 100,
                           'request_delta_percent': (b['client_total_s'] / a['client_total_s'] - 1) * 100,
                           'api_content_equal': off['api_content'] == candidate['api_content']})
        deltas = [row['decode_tps_delta_percent'] for row in paired]
        comparisons.append({'window': window, 'paired_blocks': paired,
                            'median_decode_tps_delta_percent': statistics.median(deltas) if deltas else None,
                            'bootstrap_95pct_median_interval_percent': interval(deltas, args.seed + window) if len(deltas) == args.blocks else None,
                            'failures': failures,
                            'qualified_for_timing_interpretation': not failures and len(paired) == args.blocks})
    campaign['comparisons'] = comparisons
    campaign['finished_wall_time_s'] = time.time()
    write_result(path, campaign)
    print(json.dumps(comparisons, sort_keys=True))
    return int(any(not row['qualified_for_timing_interpretation'] for row in comparisons))


if __name__ == '__main__':
    raise SystemExit(main())
