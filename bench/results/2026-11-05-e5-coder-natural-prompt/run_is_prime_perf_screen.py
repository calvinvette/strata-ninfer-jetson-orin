#!/usr/bin/env python3
"""Three randomized warmup/measurement pairs for the corrected Coder backend."""
from __future__ import annotations

import hashlib
import json
import os
import random
import statistics
import sys
import threading
import time
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration'),
                str(ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt')]
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer
from run_is_prime_state_pair import (BASE, CASES, TASK, compile_generated_function,
                                     extract_function, file_sha256)


def measure(engine: StrataEngine, prompt: list[int], budget: int, tokenizer,
            *, validate: bool) -> dict:
    started = time.monotonic()
    first_token_s = None
    ids = []
    for value in engine.generate(prompt, budget, {'temperature': 0}, threading.Event()):
        if value is None:
            continue
        if first_token_s is None:
            first_token_s = time.monotonic()
        ids.append(int(value))
    ended = time.monotonic()
    if not ids or first_token_s is None:
        raise RuntimeError('request returned no output tokens')
    last = dict(engine.last)
    row = {
        'token_ids': ids,
        'text': tokenizer.decode(ids),
        'finish': last.get('finish'),
        'prompt_tokens': int(last['prompt_tokens']),
        'generated_tokens': len(ids),
        'prompt_ms': float(last['prompt_ms']),
        'decode_ms': float(last['decode_ms']),
        'prompt_tps': int(last['prompt_tokens']) / (float(last['prompt_ms']) / 1000.0),
        'decode_tps': len(ids) / (float(last['decode_ms']) / 1000.0),
        'client_first_token_ms': (first_token_s - started) * 1000.0,
        'client_total_ms': (ended - started) * 1000.0,
        'expert_hits': int(last.get('hits', 0)),
        'expert_lookups': int(last.get('lookups', 0)),
        'file_mb': float(last.get('file_mb', 0.0)),
        'drafts_accepted': int(last.get('drafts_accepted', 0)),
        'drafts_offered': int(last.get('drafts_offered', 0)),
    }
    row['ttft_scope'] = 'client request start through first streamed token'
    row['decode_tps_scope'] = 'generated token count divided by server decode_ms; includes first token per engine counter'
    if validate:
        body = row['text'].split('<|im_end|>', 1)[0].strip()
        function = extract_function(body)
        is_prime = compile_generated_function(function)
        actual = {str(n): bool(is_prime(n)) for n in CASES}
        expected = {str(n): value for n, value in CASES.items()}
        row['function'] = function
        row['quality_cases'] = actual
        row['quality_pass'] = actual == expected
    return row


def bootstrap_median(values: list[float], seed: int = 20261105, n_boot: int = 20000) -> list[float]:
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(n_boot))
    return [samples[int(0.025 * n_boot)], samples[min(n_boot - 1, int(0.975 * n_boot))]]


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    order_arg = next((arg.split('=', 1)[1] for arg in sys.argv[2:]
                      if arg.startswith('--orders=')), None)
    if order_arg is None:
        rng = random.Random(20261105)
        orders = []
        for _ in range(3):
            order = ['strata', 'ninfer']
            rng.shuffle(order)
            orders.append(order)
        study = 'three-pair randomized same-profile Coder IQ1_M screen'
    else:
        orders = [[backend.strip() for backend in pair.split(',')]
                  for pair in order_arg.split(';')]
        if any(len(order) != 2 or sorted(order) != ['ninfer', 'strata'] for order in orders):
            raise ValueError('--orders must be semicolon-separated strata,ninfer or ninfer,strata pairs')
        counts = {order[0]: sum(pair[0] == order[0] for pair in orders)
                  for order in orders}
        if len(orders) < 4 or counts.get('strata', 0) != counts.get('ninfer', 0):
            raise ValueError('explicit screening order must have at least four pairs balanced by first backend')
        study = f'{len(orders)}-pair order-balanced same-profile Coder IQ1_M screen'
    output.mkdir(parents=True, exist_ok=False)
    command = json.loads(BASE.read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    args[args.index('--max-new') + 1] = '128'
    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    prompt = tokenizer.encode(template.render([{'role': 'user', 'content': TASK}],
                                             enable_thinking=False), parse_special=True)
    env = os.environ.copy()
    env['STRATA_PREFILL_CPU_SHARE'] = '0'
    profile = Path(args[args.index('--expert-profile') + 1])
    models = [Path(args[args.index(flag) + 1]) for flag in ('--native', '--ple-gguf')]
    blocks = []
    for block, order in enumerate(orders):
        block_result = {'block': block + 1, 'order': order, 'arms': []}
        for backend in order:
            arm_args = args.copy()
            arm_args[arm_args.index('--expert-backend') + 1] = backend
            if backend == 'ninfer':
                arm_args.append('--expert-backend-strict')
            log = output / f'block-{block + 1}-{backend}.log'
            engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
            try:
                startup = dict(engine.info)
                warm = measure(engine, prompt, 8, tokenizer, validate=False)
                measured = measure(engine, prompt, 128, tokenizer, validate=True)
                block_result['arms'].append({'backend': backend,
                                             'warmup': {'generated_tokens': warm['generated_tokens'],
                                                        'finish': warm['finish']},
                                             'measured': measured, 'log': log.name,
                                             'engine_info': startup})
            finally:
                engine.close()
        blocks.append(block_result)

    pairs = []
    metric_pairs = {'decode_tps_gain_pct': [], 'prompt_tps_gain_pct': [],
                    'ttft_reduction_pct': [], 'client_time_reduction_pct': []}
    for block in blocks:
        by_backend = {row['backend']: row['measured'] for row in block['arms']}
        s, n = by_backend['strata'], by_backend['ninfer']
        for metric in metric_pairs:
            if metric == 'decode_tps_gain_pct':
                effect = (n['decode_tps'] / s['decode_tps'] - 1) * 100
            elif metric == 'prompt_tps_gain_pct':
                effect = (n['prompt_tps'] / s['prompt_tps'] - 1) * 100
            elif metric == 'ttft_reduction_pct':
                effect = (1 - n['client_first_token_ms'] / s['client_first_token_ms']) * 100
            else:
                effect = (1 - n['client_total_ms'] / s['client_total_ms']) * 100
            metric_pairs[metric].append(effect)
        pairs.append({'block': block['block'], 'tokens_equal': s['token_ids'] == n['token_ids'],
                      'quality_pass_both': s['quality_pass'] and n['quality_pass'],
                      'generated_counts': [s['generated_tokens'], n['generated_tokens']],
                      'expert_hits': [s['expert_hits'], n['expert_hits']],
                      'expert_lookups': [s['expert_lookups'], n['expert_lookups']]})

    summaries = {}
    for metric, values in metric_pairs.items():
        summaries[metric] = {'pair_effects_pct': values,
                             'paired_median_pct': statistics.median(values),
                             'paired_bootstrap_95_pct': bootstrap_median(values)}
    result = {
        'date': '2026-11-05', 'hardware': 'Jetson Orin AGX, SM87, CUDA 12.6',
        'study': study,
        'primary_metric': 'server decode tokens/s; generated_tokens / decode_ms includes the first token',
        'warmup': 'one eight-token same-prompt request per fresh arm process; measured request follows in that process',
        'context_tokens': 512, 'max_new': 128, 'prompt_tokens': len(prompt),
        'prompt_ids_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
        'temperature': 0, 'accepted_prefix_trace': False, 'state_hash': False,
        'expert_profile_sha256': file_sha256(profile),
        'binary_sha256': file_sha256(Path(executable)),
        'model_shards': [{'name': p.name, 'bytes': p.stat().st_size,
                          'sha256': ['e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad',
                                     '316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113'][i]}
                         for i, p in enumerate(models)],
        'profile': profile.name,
        'profile_slot_arg': args[args.index('--expert-cache') + 1],
        'runtime_options': {'prefill_chunk': args[args.index('--prefill') + 1],
                            'context': args[args.index('--max-context') + 1],
                            'spec': args[args.index('--spec') + 1],
                            'prompt_cache': args[args.index('--prompt-cache') + 1],
                            'prefill_cpu_share': 0},
        'orders': orders, 'blocks': blocks, 'paired_quality': pairs, 'summary': summaries,
        'limits': [f'{len(orders)} pairs are screen-only; confirmation is not implied',
                   'dynamic clocks; no clock controls', 'EMC readback denied',
                   'energy not measured',
                   'explicit pair orders are fixed, not randomized' if order_arg is not None
                   else 'pair order is seeded-randomized',
                   'client timing is sequential and instrumented by the harness']
    }
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'paired_quality': pairs, 'summary': summaries}, indent=2))
    return 0 if all(p['tokens_equal'] and p['quality_pass_both'] for p in pairs) else 2


if __name__ == '__main__':
    raise SystemExit(main())
