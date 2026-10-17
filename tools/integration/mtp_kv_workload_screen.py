"""Randomized blocked Coder MTP × KV-format × prompt-length screen."""
from __future__ import annotations

import argparse
import hashlib
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
from summarize_controls import metrics


def expected_answer(workload):
    codes = workload.get('expected_codes')
    if not isinstance(codes, list) or len(codes) != 3:
        raise ValueError(f"{workload.get('cell')}: expected exactly three independent marker codes")
    answer = f"EARLY={codes[0]}, MIDDLE={codes[1]}, LATE={codes[2]}"
    suffix_sum = workload.get('expected_suffix_sum')
    if suffix_sum is not None:
        answer += f", SUM={suffix_sum}"
    return answer


def replace_option(args, name, value):
    result = list(args)
    if name in result:
        result[result.index(name) + 1] = str(value)
    else:
        result += [name, str(value)]
    return result


def stable_arm_name(block, kv, workload, window):
    return f"block-{block:02d}-kv-{kv}-workload-{workload}-mtp-{window}"


def arm_key(row):
    return row['block'], row['kv'], row['workload'], row['window']


def attempt_name(cell, runs, output):
    """Return a non-overwriting directory name for a new or pressure-retried arm."""
    key = arm_key(cell)
    previous = [run for run in runs if arm_key(run) == key]
    if any(run.get('status') == 'pass' for run in previous):
        return None
    for run in previous:
        if (run.get('status') != 'fail' or
                run.get('supervisor_status') != 'pressure_abort'):
            raise ValueError(f"cannot resume {key}: prior attempt did not end in a pressure abort")
    base = stable_arm_name(*key)
    if not previous and not (output / base).exists():
        return base
    retry = len(previous)
    while True:
        name = f'{base}-retry-{retry:02d}'
        if not (output / name).exists():
            return name
        retry += 1


def make_design(kvs, workloads, windows, blocks, seed):
    cells = [(kv, workload, window)
             for kv in kvs for workload in workloads for window in windows]
    rng = random.Random(seed)
    return [{'block': block, 'order': order,
             'kv': kv, 'workload': workload, 'window': window}
            for block in range(blocks)
            for order, (kv, workload, window) in enumerate(rng.sample(cells, len(cells)))]


def bootstrap_interval(values, seed, draws=10000):
    if len(values) < 2:
        return [None, None]
    rng = random.Random(seed)
    estimates = sorted(statistics.median(rng.choices(values, k=len(values)))
                       for _ in range(draws))
    return [estimates[int(0.025 * draws)], estimates[int(0.975 * draws)]]


def summarize_factorial(rows, workloads, kvs, windows, seed):
    by_key = {(r['block'], r['kv'], r['workload'], r['window']): r for r in rows}
    metrics_names = ('prompt_tps', 'decode_tps', 'client_ttft_s', 'client_total_s')
    result = {'cell_effects': [], 'mtp_by_kv_interactions': [],
              'mtp_by_workload_interactions': [], 'three_way_interactions': []}
    effects = {}
    for workload in workloads:
        for kv in kvs:
            paired = []
            for block in range(max(r['block'] for r in rows) + 1):
                control = by_key[(block, kv, workload, 0)]
                candidate = by_key[(block, kv, workload, windows[-1])]
                pair = {'block': block}
                for name in metrics_names:
                    pair[name + '_ratio'] = candidate['metrics'][name] / control['metrics'][name]
                paired.append(pair)
            effects[(kv, workload)] = paired
            summary = {'kv_format': kv, 'workload': workload, 'paired_blocks': len(paired)}
            for name in metrics_names:
                ratios = [p[name + '_ratio'] for p in paired]
                summary[name + '_mtp4_effect_percent'] = (statistics.median(ratios) - 1) * 100
                interval = bootstrap_interval(
                    ratios, seed + len(result['cell_effects']) * 101 + len(name))
                summary[name + '_paired_bootstrap_95_interval_percent'] = [
                    (x - 1) * 100 if x is not None else None for x in interval]
                summary[name + '_paired_ratios'] = ratios
            result['cell_effects'].append(summary)

    for workload in workloads:
        paired_rows = []
        for block in range(max(r['block'] for r in rows) + 1):
            row = {'block': block}
            for metric in metrics_names:
                fp16_ratio = effects[('fp16', workload)][block][metric + '_ratio']
                int8_ratio = effects[('int8', workload)][block][metric + '_ratio']
                row[metric + '_int8_vs_fp16_interaction_percent'] = (int8_ratio / fp16_ratio - 1) * 100
            paired_rows.append(row)
        item = {'workload': workload, 'paired_blocks': len(paired_rows)}
        for metric in metrics_names:
            values = [r[metric + '_int8_vs_fp16_interaction_percent'] for r in paired_rows]
            item[metric + '_median_interaction_percent'] = statistics.median(values)
            item[metric + '_paired_bootstrap_95_interval_percent'] = bootstrap_interval(values, seed + 4000 + len(item) + len(metric))
            item[metric + '_paired_values_percent'] = values
        result['mtp_by_kv_interactions'].append(item)

    if len(workloads) >= 2:
        for kv in kvs:
            paired_rows = []
            for block in range(max(r['block'] for r in rows) + 1):
                row = {'block': block}
                for metric in metrics_names:
                    short = effects[(kv, workloads[0])][block][metric + '_ratio']
                    long = effects[(kv, workloads[1])][block][metric + '_ratio']
                    row[metric + '_long_vs_short_interaction_percent'] = (long / short - 1) * 100
                paired_rows.append(row)
            item = {'kv_format': kv, 'workloads': [workloads[0], workloads[1]], 'paired_blocks': len(paired_rows)}
            for metric in metrics_names:
                values = [r[metric + '_long_vs_short_interaction_percent'] for r in paired_rows]
                item[metric + '_median_interaction_percent'] = statistics.median(values)
                item[metric + '_paired_bootstrap_95_interval_percent'] = bootstrap_interval(values, seed + 5000 + len(item) + len(metric))
                item[metric + '_paired_values_percent'] = values
            result['mtp_by_workload_interactions'].append(item)

        for block in range(max(r['block'] for r in rows) + 1):
            item = {'block': block}
            for metric in metrics_names:
                def ratio(kv, workload):
                    return effects[(kv, workload)][block][metric + '_ratio']
                short_kv = ratio('int8', workloads[0]) / ratio('fp16', workloads[0])
                long_kv = ratio('int8', workloads[1]) / ratio('fp16', workloads[1])
                item[metric + '_three_way_interaction_percent'] = (long_kv / short_kv - 1) * 100
            result['three_way_interactions'].append(item)
        for metric in metrics_names:
            values = [row[metric + '_three_way_interaction_percent'] for row in result['three_way_interactions']]
            result['three_way_summary'] = result.get('three_way_summary', {})
            result['three_way_summary'][metric] = {
                'median_percent': statistics.median(values),
                'paired_bootstrap_95_interval_percent': bootstrap_interval(values, seed + 6000 + len(metric)),
                'paired_values_percent': values,
            }
    return result


def request_record(path):
    data = json.loads(path.read_text())
    rows = [row for row in data.get('checks', []) if not row.get('warmup')]
    if len(rows) != 1:
        raise ValueError(f'expected one measured API request, found {len(rows)}')
    row = rows[0]
    if row.get('status') != 'pass':
        raise ValueError(f"measured request failed: {row.get('reason')}")
    return row


def window_clocks(run_dir, request):
    memory = [json.loads(line) for line in (run_dir / 'supervisor/memory.jsonl').read_text().splitlines() if line]
    start, end = request.get('request_start_monotonic_s'), request.get('request_end_monotonic_s')
    selected = [row for row in memory if start is not None and end is not None and start <= row.get('monotonic_s', -1) <= end]
    def range_for(key):
        values = [row.get('clock_observations', {}).get(key, {}).get('hz') for row in selected]
        values = [v / 1e6 for v in values if isinstance(v, (int, float))]
        return {'samples': len(values), 'min_mhz': min(values) if values else None,
                'max_mhz': max(values) if values else None}
    return {'sample_count': len(selected), 'gpu': range_for('gpu'), 'emc': range_for('emc')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--warmup-workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workload-cells', nargs='+', required=True,
                        help='one held-out workload or short then long workload cells')
    parser.add_argument('--kvs', nargs=2, default=['fp16', 'int8'], choices=['fp16', 'int8'])
    parser.add_argument('--windows', nargs=2, type=int, default=[0, 4])
    parser.add_argument('--blocks', type=int, default=3)
    parser.add_argument('--seed', type=int, default=20261023)
    parser.add_argument('--first-port', type=int, default=19400)
    parser.add_argument('--expert-cache-budget', type=int,
                        help='override the configured --expert-cache budget for this screen')
    parser.add_argument('--resume', action='store_true',
                        help='continue a failed campaign, preserving completed and aborted attempts')
    parser.add_argument('--per-arm-memory-max',
                        help='place each arm in a fresh systemd scope with this MemoryMax (for example 28G)')
    parser.add_argument('--followup-block', action='store_true',
                        help='permit exactly one explicitly labelled randomized block for a screened-cell follow-up')
    args = parser.parse_args()
    if args.output.exists() != args.resume:
        parser.error('use --resume only with an existing campaign output directory')
    if args.expert_cache_budget is not None and args.expert_cache_budget <= 0:
        parser.error('--expert-cache-budget must be positive')
    if (args.blocks < 3 and not (args.followup_block and args.blocks == 1)) or (args.followup_block and args.blocks != 1):
        parser.error('use at least three blocks for a screen; --followup-block permits exactly one block')
    if args.windows != [0, 4] or args.kvs != ['fp16', 'int8']:
        parser.error('this screen requires MTP windows 0/4 and KV formats fp16/int8')
    if len(args.workload_cells) not in (1, 2):
        parser.error('select one held-out workload or a short/long workload pair')
    cfg = json.loads(args.config.read_text())
    workload_rows = json.loads(args.workloads.read_text()).get('workloads', [])
    workload_by_cell = {row.get('cell'): row for row in workload_rows}
    warmups = json.loads(args.warmup_workloads.read_text())
    selected = [workload_by_cell.get(cell) for cell in args.workload_cells]
    if any(row is None for row in selected):
        parser.error('one or more selected workload cells are absent')
    workloads = {row['cell']: row for row in selected}
    if len(selected) == 2 and selected[0]['prompt_tokens'] >= selected[1]['prompt_tokens']:
        parser.error('workload-cells must be ordered from short to long prompt')
    for row in selected:
        expected_answer(row)
    for workload in workloads.values():
        if workload['generate_tokens'] <= 0:
            parser.error('selected workload must request generated tokens')

    design = make_design(args.kvs, args.workload_cells, args.windows, args.blocks, args.seed)
    binary_path = Path(cfg['exe'])
    binary_sha = hashlib.sha256(binary_path.read_bytes()).hexdigest()
    if args.followup_block:
        scope = ('single randomized 2×2×2 follow-up block; not a standalone screen'
                 if len(args.workload_cells) == 2 else
                 'single randomized 2×2 MTP-window × KV-format follow-up block; not a standalone screen')
    elif len(args.workload_cells) == 1:
        scope = 'randomized blocked 2×2 MTP-window × KV-format screen on one held-out workload'
    else:
        scope = 'randomized blocked 2×2×2 MTP-window × KV-format × prompt-length screen'
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if args.resume:
        campaign_path = args.output / 'campaign.json'
        if not campaign_path.exists():
            parser.error('--resume requires campaign.json')
        campaign = json.loads(campaign_path.read_text())
        expected = {'binary_sha256': binary_sha, 'workloads': args.workload_cells,
                    'kv_formats': args.kvs, 'mtp_windows': args.windows, 'blocks': args.blocks,
                    'expert_cache_budget_override': args.expert_cache_budget, 'seed': args.seed,
                    'randomized_design': design, 'model_name': cfg.get('model_name'),
                    'prompt_tokens_requested': {cell: workloads[cell]['prompt_tokens']
                                                for cell in args.workload_cells}}
        mismatches = [key for key, value in expected.items() if campaign.get(key) != value]
        selected_path = args.output / 'selected-workloads.json'
        if selected_path.exists():
            prior_workloads = json.loads(selected_path.read_text()).get('workloads')
            if prior_workloads != selected:
                mismatches.append('selected-workloads')
        else:
            mismatches.append('selected-workloads')
        if mismatches:
            parser.error('--resume campaign does not match: ' + ', '.join(mismatches))
        if campaign.get('status') == 'pass':
            parser.error('campaign is already complete')
        if args.per_arm_memory_max:
            campaign.setdefault('resume_memory_scopes', []).append({
                'wall_time_s': time.time(), 'mode': 'per-arm',
                'memory_max': args.per_arm_memory_max,
                'runner_source_commit': source_commit})
        campaign['status'] = 'running'
        write_result(campaign_path, campaign)
    else:
        args.output.mkdir(parents=True)
        campaign = {'schema': 1, 'scope': scope, 'source_commit': source_commit,
                    'binary': str(binary_path), 'binary_sha256': binary_sha,
                    'model_name': cfg.get('model_name'), 'workloads': args.workload_cells,
                    'prompt_tokens_requested': {cell: workloads[cell]['prompt_tokens'] for cell in args.workload_cells},
                    'kv_formats': args.kvs, 'mtp_windows': args.windows, 'blocks': args.blocks,
                    'expert_cache_budget_override': args.expert_cache_budget,
                    'seed': args.seed, 'floor_gib': 6, 'supervisor_memory_max': '28G',
                    'randomized_design': design, 'runs': [], 'status': 'running'}
        if args.per_arm_memory_max:
            campaign['memory_scope_mode'] = 'per-arm'
            campaign['supervisor_memory_max'] = args.per_arm_memory_max
        write_result(args.output / 'campaign.json', campaign)
        (args.output / 'config-source.json').write_text(json.dumps(cfg, indent=2) + '\n')
        (args.output / 'selected-workloads.json').write_text(json.dumps({'workloads': selected}, indent=2) + '\n')

    for index, cell in enumerate(design):
        block, kv, workload_cell, window = cell['block'], cell['kv'], cell['workload'], cell['window']
        try:
            run_name = attempt_name(cell, campaign['runs'], args.output)
        except ValueError as exc:
            campaign['status'] = 'failed'
            campaign['failure_reason'] = str(exc)
            write_result(args.output / 'campaign.json', campaign)
            return 1
        if run_name is None:
            continue
        run_dir = args.output / run_name
        run_dir.mkdir()
        arm_args = args_for(cfg, window, kv_format=kv, disable_adaptive_swaps=True)
        if args.expert_cache_budget is not None:
            arm_args = replace_option(arm_args, '--expert-cache', args.expert_cache_budget)
        arm_args = replace_option(arm_args, '--prompt-cache', 0)
        port = args.first_port + index
        run_cfg = dict(cfg, args=arm_args, port=port,
                       log=str((run_dir / 'engine.log').resolve()))
        config_path = run_dir / 'config.json'
        config_path.write_text(json.dumps(run_cfg, indent=2) + '\n')
        one_workload = run_dir / 'workload.json'
        one_workload.write_text(json.dumps({'workloads': [workloads[workload_cell]]}, indent=2) + '\n')
        command = [sys.executable, str(ROOT / 'tools/integration/run_control.py'),
                   '--output', str((run_dir / 'supervisor').resolve()), '--timeout', '1800',
                   '--interval', '1', '--sample-clocks', '--',
                   sys.executable, str(ROOT / 'tools/integration/api_control_block.py'),
                   '--config', str(config_path.resolve()), '--workloads', str(one_workload.resolve()),
                   '--output', str((run_dir / 'requests.json').resolve()), '--variant', 'candidate',
                   '--rounds', '1', '--no-trace', '--warmup-workloads', str(args.warmup_workloads.resolve())]
        if args.per_arm_memory_max:
            command = ['systemd-run', '--user', '--scope', '--collect',
                       '-p', f'MemoryMax={args.per_arm_memory_max}', '-p', 'IOAccounting=yes',
                       '--', *command]
        record = dict(cell, name=run_name, directory=run_name, command=command, status='started')
        if args.per_arm_memory_max:
            record['supervisor_memory_max'] = args.per_arm_memory_max
        campaign['runs'].append(record)
        write_result(args.output / 'campaign.json', campaign)
        with (run_dir / 'launch.txt').open('w') as log:
            rc = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        supervisor_path = run_dir / 'supervisor/result.json'
        if not supervisor_path.exists():
            record.update(status='fail', reason='missing supervisor result', returncode=rc)
            write_result(args.output / 'campaign.json', campaign)
            return 1
        supervisor = json.loads(supervisor_path.read_text())
        record.update(supervisor_status=supervisor.get('status'), supervisor_returncode=supervisor.get('returncode'),
                      elapsed_s=supervisor.get('elapsed_s'),
                      minimum_available_bytes=supervisor.get('minimum_available_bytes'),
                      minimum_admission_available_bytes=supervisor.get('minimum_admission_available_bytes'))
        try:
            if rc != 0 or supervisor.get('status') != 'pass':
                raise ValueError(f"supervisor/launcher failed: {supervisor.get('status')} rc={rc}")
            request = request_record(run_dir / 'requests.json')
            expected = expected_answer(workloads[workload_cell])
            message = request['response']['choices'][0]['message']
            answer = message.get('content', '').strip()
            if answer != expected:
                raise ValueError(f'independent retrieval oracle mismatch: {answer!r} != {expected!r}')
            observed = metrics(request)
            if observed['prompt_tokens'] != workloads[workload_cell]['prompt_tokens']:
                raise ValueError(f"actual prompt length {observed['prompt_tokens']} != {workloads[workload_cell]['prompt_tokens']}")
            engine = request.get('metrics_after', {}).get('engine', {})
            if engine.get('kv') != kv:
                raise ValueError(f"requested KV {kv}, engine reported {engine.get('kv')!r}")
            if not isinstance(engine.get('expert_slots'), int) or engine['expert_slots'] <= 0:
                raise ValueError('actual expert residency is missing')
            if window == 4 and (not observed.get('drafted') or not observed.get('accepted')):
                raise ValueError('MTP4 did not draft and accept tokens')
            if supervisor['minimum_available_bytes'] < 6 * (1 << 30):
                raise ValueError('six-GiB physical availability floor failed')
            record.update(status='pass', request_status=request['status'], answer=answer,
                          metrics=observed, engine={k: engine.get(k) for k in ('kv', 'expert_slots', 'expert_cache_mib', 'mtp_max', 'spec')},
                          clock_window=window_clocks(run_dir, request))
        except Exception as exc:
            record.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
            campaign['status'] = 'failed'
            write_result(args.output / 'campaign.json', campaign)
            return 1
        write_result(args.output / 'campaign.json', campaign)

    campaign['unfiltered_comparisons_do_not_account_for_residency'] = summarize_factorial(
        campaign['runs'], args.workload_cells, args.kvs, args.windows, args.seed)
    from audit_mtp_kv_screen import audit
    campaign['comparisons'] = audit(campaign, args.seed, args.output)
    campaign['status'] = 'pass'
    campaign['finished_wall_time_s'] = time.time()
    write_result(args.output / 'campaign.json', campaign)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
