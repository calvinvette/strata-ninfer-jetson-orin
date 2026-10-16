#!/usr/bin/env python3
"""Seven-block randomized Q2_0 capture × MTP2 processor-quality confirmation."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PYTHON = Path('/home/calvin/.local/python/bin/python3')
BASE_CONFIG = Path('/home/calvin/workspace/strata-ninfer-jetson-orin/bench/results/2026-10-14-phase5-phase6-graph-mtp-screen/config-captured-mtp0.json')
WARMUPS = Path('/home/calvin/workspace/strata-ninfer-jetson-orin/bench/results/2026-10-14-phase5-phase6-graph-mtp-screen/warmup-workloads.json')
CONDITIONS = ('captured-mtp0', 'eager-mtp0', 'captured-mtp2', 'eager-mtp2')


def without_factors(argv):
    result, i = [], 0
    while i < len(argv):
        if argv[i] in ('--no-capture', '--mtp', '--mtp-max-t'):
            i += 1 if argv[i] == '--no-capture' else 2
        else:
            result.append(argv[i])
            i += 1
    return result


def pct_ratio(numerator, denominator):
    return 100.0 * (numerator / denominator - 1.0)


def bootstrap_interval(values, seed):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(20000))
    return [samples[int(.025 * len(samples))], samples[int(.975 * len(samples))]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--blocks', type=int, default=7)
    ap.add_argument('--seed', type=int, default=202610143)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.blocks < 7:
        ap.error('confirmation requires at least seven independent blocks')
    if args.output.exists():
        ap.error('output path already exists')
    base = json.loads(BASE_CONFIG.read_text())
    schedule = []
    rng = random.Random(args.seed)
    for block in range(args.blocks):
        cells = list(CONDITIONS)
        rng.shuffle(cells)
        schedule.extend({'block': block, 'condition': cell, 'status': 'not_run'} for cell in cells)
    print(json.dumps({'seed': args.seed, 'blocks': args.blocks, 'schedule': schedule}, indent=2))
    if not args.run:
        return 0

    args.output.mkdir(parents=True, exist_ok=False)
    configs = {}
    for condition in CONDITIONS:
        cfg = json.loads(json.dumps(base))
        argv = list(cfg['args'])
        if condition.startswith('eager-'):
            argv.append('--no-capture')
        if condition.endswith('mtp2'):
            argv.extend(['--mtp', '/home/calvin/models/strata-orin-validation/mtp/rt', '--mtp-max-t', '2'])
        if '--adapt-accepted-only' not in argv or '--adapt-every' not in argv:
            ap.error('accepted-only swap policy is required for every arm')
        if ('--no-capture' in argv) != condition.startswith('eager-'):
            ap.error(f'{condition}: capture factor mismatch')
        if ('--mtp' in argv) != condition.endswith('mtp2'):
            ap.error(f'{condition}: MTP factor mismatch')
        cfg['args'] = argv
        cfg['model_name'] = f'Q2_0 Phase 6 held-out graph × MTP confirmation {condition}'
        cfg['port'] = 18680 + CONDITIONS.index(condition)
        cfg['log'] = ''
        path = args.output / f'config-{condition}.json'
        path.write_text(json.dumps(cfg, indent=2) + '\n')
        configs[condition] = path
    canonical = {tuple(without_factors(json.loads(p.read_text())['args'])) for p in configs.values()}
    if len(canonical) != 1:
        ap.error('non-factor configuration changed across arms')

    campaign = {
        'schema': 1,
        'design': 'seven-block randomized 2×2 confirmation: capture × MTP2',
        'seed': args.seed,
        'blocks': args.blocks,
        'workloads': str((HERE / 'workloads.json').resolve()),
        'warmup_workloads': str(WARMUPS.resolve()),
        'binary_sha256': subprocess.check_output(['sha256sum', str(ROOT / 'build/integration/candidate/strata')], text=True).split()[0],
        'scope': 'distinct 512/1 warmup and validated 2094-token processor quality request (up to 512 output) per fresh service; accepted-only swap cadence; trace disabled',
        'started_wall_time_s': time.time(),
        'runs': schedule,
    }
    manifest = args.output / 'campaign.json'
    manifest.write_text(json.dumps(campaign, indent=2) + '\n')
    tools = ROOT / 'tools/integration'
    for index, row in enumerate(campaign['runs']):
        condition = row['condition']
        run_dir = args.output / f"block-{row['block']:02d}-{condition}"
        run_dir.mkdir()
        request_path = run_dir / 'requests.json'
        command = [str(PYTHON), str(tools / 'run_control.py'), '--output', str((run_dir / 'supervisor').resolve()),
                   '--timeout', '1800', '--interval', '1', '--sample-clocks', '--',
                   str(PYTHON), str(tools / 'api_control_block.py'), '--config', str(configs[condition].resolve()),
                   '--workloads', str((HERE / 'workloads.json').resolve()), '--warmup-workloads', str(WARMUPS.resolve()),
                   '--output', str(request_path.resolve()), '--variant', 'candidate' if condition.startswith('captured-') else 'baseline',
                   '--rounds', '1', '--no-trace']
        row.update(command=command, directory=str(run_dir.resolve()), status='running')
        manifest.write_text(json.dumps(campaign, indent=2) + '\n')
        print('starting', run_dir.name, flush=True)
        with (run_dir / 'launch.txt').open('w') as log:
            code = subprocess.call(['systemd-run', '--user', '--scope', '--collect', '-p', 'MemoryMax=28G', '-p', 'IOAccounting=yes', *command], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        sup_path = run_dir / 'supervisor' / 'result.json'
        if sup_path.exists():
            sup = json.loads(sup_path.read_text())
            row.update(status=sup['status'], supervisor_returncode=code,
                       minimum_available_bytes=sup.get('minimum_available_bytes'),
                       minimum_admission_available_bytes=sup.get('minimum_admission_available_bytes'),
                       elapsed_s=sup.get('elapsed_s'), reason=sup.get('reason'))
        else:
            row.update(status='fail', supervisor_returncode=code, reason='missing terminal supervisor record')
        if row['status'] == 'pass':
            req = json.loads((run_dir / 'requests.json').read_text())
            measured = [item for item in req['checks'] if not item.get('warmup')]
            if len(measured) != 1 or measured[0].get('status') != 'pass':
                row.update(status='fail', reason='measured request did not pass API qualification')
            else:
                answer = measured[0]['response']['choices'][0]['message']['content']
                usage = measured[0]['response']['usage']
                request_metrics = measured[0].get('metrics_after', {}).get('requests', [])
                raw = next((m for m in request_metrics if m.get('prompt_tokens') == usage.get('prompt_tokens') and m.get('output_tokens') == usage.get('completion_tokens')), None)
                words = answer.split()
                lower = answer.lower()
                if (usage.get('prompt_tokens') != 2094 or usage.get('completion_tokens') < 200 or
                        raw is None or raw.get('finish') != 'stop' or
                        not answer.startswith('Processor:') or len(words) < 200 or
                        any(term.lower() not in lower for term in ('fetch', 'decode', 'execute', 'RAM', 'binary', 'input', 'output', '17 x 19 = 323'))):
                    row.update(status='fail', reason=f'processor quality gate failed: usage={usage}; starts={answer[:40]!r}; words={len(words)}')
        manifest.write_text(json.dumps(campaign, indent=2) + '\n')
        print('finished', run_dir.name, row['status'], flush=True)
        if code or row['status'] != 'pass':
            for pending in campaign['runs'][index + 1:]:
                pending.update(status='not_run', reason='not launched after failed or pressure-aborted cell')
            manifest.write_text(json.dumps(campaign, indent=2) + '\n')
            return 1

    # Extract paired request observations and verify exact configuration/output parity.
    block_rows = []
    for block in range(args.blocks):
        data = {}
        for condition in CONDITIONS:
            run = args.output / f'block-{block:02d}-{condition}'
            req = json.loads((run / 'requests.json').read_text())
            rows = [r for r in req['checks'] if not r.get('warmup')]
            if len(rows) != 1 or rows[0]['status'] != 'pass':
                raise RuntimeError(f'{run.name}: expected one qualified measured request')
            item = rows[0]
            timings = item['response']['timings']
            met = item.get('metrics_after', {}).get('requests', [])
            raw = next((m for m in met if m.get('prompt_tokens') == item['response']['usage']['prompt_tokens'] and m.get('output_tokens') == item['response']['usage']['completion_tokens']), None)
            if raw is None or raw.get('reused') or raw.get('prompt_read') != item['response']['usage']['prompt_tokens']:
                raise RuntimeError(f'{run.name}: missing fresh-prefill request counters')
            content = item['response']['choices'][0]['message']['content']
            usage = item['response']['usage']
            if usage.get('prompt_tokens') != 2094 or usage.get('completion_tokens') < 200:
                raise RuntimeError(f'{run.name}: task token identity changed: {usage}')
            if raw.get('finish') != 'stop':
                raise RuntimeError(f'{run.name}: quality answer did not stop naturally')
            words = content.split()
            lowered = content.lower()
            required = ('Processor:', 'fetch', 'decode', 'execute', 'RAM', 'binary', 'input', 'output', '17 x 19 = 323')
            if len(words) < 200 or any(term.lower() not in lowered for term in required):
                raise RuntimeError(f'{run.name}: processor task rubric failed')
            sup = json.loads((run / 'supervisor' / 'result.json').read_text())
            data[condition] = {
                'text': content,
                'text_sha256': hashlib.sha256(content.encode()).hexdigest(),
                'prompt_tokens': item['response']['usage']['prompt_tokens'],
                'completion_tokens': item['response']['usage']['completion_tokens'],
                'finish_reason': item['response']['choices'][0].get('finish_reason'),
                'client_elapsed_s': item['client_elapsed_s'],
                'client_ttft_s': item.get('stream_observation', {}).get('first_visible_delta_s'),
                'prompt_ms': timings.get('prompt_ms'),
                'decode_ms': timings.get('predicted_ms'),
                'decode_tps': raw.get('decode_tok_s'),
                'drafts_offered': raw.get('drafts_offered'),
                'drafts_accepted': raw.get('drafts_accepted'),
                'expert_slots': item['metrics_after']['engine'].get('expert_slots'),
                'kv': item['metrics_after']['engine'].get('kv'),
                'minimum_available_bytes': sup.get('minimum_available_bytes'),
                'minimum_admission_available_bytes': sup.get('minimum_admission_available_bytes'),
            }
        expected = {(v['prompt_tokens'], v['completion_tokens'], v['expert_slots'], v['kv']) for v in data.values()}
        if len(expected) != 1:
            raise RuntimeError(f'block {block}: prompt/output/resource identity mismatch: {expected}')
        block_rows.append({'block': block, 'order': [r['condition'] for r in campaign['runs'] if r['block'] == block],
                           'conditions': data,
                           'output_text_equal': len({v['text_sha256'] for v in data.values()}) == 1})

    # Each effect uses block-paired ratios. Bootstrap is over independent processes, not tokens.
    factors = {}
    definitions = {
        'capture_effect_mtp0_request': lambda b: b['captured-mtp0']['client_elapsed_s'] / b['eager-mtp0']['client_elapsed_s'],
        'capture_effect_mtp2_request': lambda b: b['captured-mtp2']['client_elapsed_s'] / b['eager-mtp2']['client_elapsed_s'],
        'mtp2_effect_captured_request': lambda b: b['captured-mtp2']['client_elapsed_s'] / b['captured-mtp0']['client_elapsed_s'],
        'mtp2_effect_eager_request': lambda b: b['eager-mtp2']['client_elapsed_s'] / b['eager-mtp0']['client_elapsed_s'],
        'capture_x_mtp_request_interaction': lambda b: (b['captured-mtp2']['client_elapsed_s'] / b['eager-mtp2']['client_elapsed_s']) / (b['captured-mtp0']['client_elapsed_s'] / b['eager-mtp0']['client_elapsed_s']),
        'capture_x_mtp_decode_interaction': lambda b: (b['captured-mtp2']['decode_tps'] / b['eager-mtp2']['decode_tps']) / (b['captured-mtp0']['decode_tps'] / b['eager-mtp0']['decode_tps']),
    }
    for i, (name, fn) in enumerate(definitions.items()):
        ratios = [fn({key: val for key, val in row['conditions'].items()}) for row in block_rows]
        factors[name] = {'paired_ratio_per_block': ratios,
                         'median_change_percent': pct_ratio(statistics.median(ratios), 1.0),
                         'paired_bootstrap_95_interval_percent': [pct_ratio(x, 1.0) for x in bootstrap_interval(ratios, args.seed + i)]}
    campaign['analysis'] = {
        'blocks': block_rows,
        'factors': factors,
        'all_outputs_equal': all(row['output_text_equal'] for row in block_rows),
        'qualified_for_performance_interpretation': all(row['output_text_equal'] for row in block_rows),
        'caveat': 'one previously validated processor-quality workload and local Q2_0 artifact; dynamic clocks and shared file cache; no energy-per-request attribution',
    }
    campaign['finished_wall_time_s'] = time.time()
    manifest.write_text(json.dumps(campaign, indent=2) + '\n')
    print(json.dumps({'all_outputs_equal': campaign['analysis']['all_outputs_equal'], 'factors': factors}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
