#!/usr/bin/env python3
"""Order-balanced Strata/strict-NInfer screen for the exact 2K Coder retrieval task."""
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
from run_is_prime_state_pair import file_sha256

BASE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
EXPECTED = '73192'
PREFIX = 'Archived closed tickets: '
FILLER = 'ticket closed code 11804; status resolved. '
SUFFIX = ('\nACTIVE TICKET: code 73192; status open. '
          'Question: return the code for the active ticket using digits only.')


def bootstrap_median(values: list[float], seed: int = 20261105, n_boot: int = 20000) -> list[float]:
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(n_boot))
    return [samples[int(0.025 * n_boot)], samples[min(n_boot - 1, int(0.975 * n_boot))]]


def measure(engine: StrataEngine, prompt: list[int], budget: int, tokenizer,
            *, validate: bool) -> dict:
    started = time.monotonic()
    first = None
    ids = []
    for value in engine.generate(prompt, budget, {'temperature': 0}, threading.Event()):
        if value is None:
            continue
        if first is None:
            first = time.monotonic()
        ids.append(int(value))
    ended = time.monotonic()
    if not ids or first is None:
        raise RuntimeError('request returned no output tokens')
    last = dict(engine.last)
    decoded = tokenizer.decode(ids).strip()
    answer = decoded.split('<|im_end|>', 1)[0].strip()
    row = {
        'token_ids': ids, 'decoded': decoded, 'answer': answer,
        'generated_tokens': len(ids), 'finish': last.get('finish'),
        'prompt_tokens': int(last['prompt_tokens']),
        'prompt_ms': float(last['prompt_ms']), 'decode_ms': float(last['decode_ms']),
        'prompt_tps': int(last['prompt_tokens']) / (float(last['prompt_ms']) / 1000),
        'decode_tps': len(ids) / (float(last['decode_ms']) / 1000),
        'client_first_token_ms': (first - started) * 1000,
        'client_total_ms': (ended - started) * 1000,
        'expert_hits': int(last.get('hits', 0)),
        'expert_lookups': int(last.get('lookups', 0)),
    }
    if validate:
        row['quality_pass'] = answer == EXPECTED
    return row


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f'usage: {sys.argv[0]} OUTPUT_DIR')
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    command = json.loads(BASE.read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    args[args.index('--max-new') + 1] = '16'
    args[args.index('--max-context') + 1] = '4096'

    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')

    def encode(content: str) -> list[int]:
        return tokenizer.encode(template.render(
            [{'role': 'user', 'content': content}], enable_thinking=False), parse_special=True)

    target = 2048
    low, high, content = 0, target, None
    while low <= high:
        count = (low + high) // 2
        candidate = PREFIX + FILLER * count + SUFFIX
        size = len(encode(candidate))
        if size == target:
            content = candidate
            break
        if size < target:
            low = count + 1
        else:
            high = count - 1
    if content is None:
        for count in range(max(0, high - 2), low + 3):
            for padding in range(1, 20):
                candidate = PREFIX + FILLER * count + 'closed ' * padding + SUFFIX
                if len(encode(candidate)) == target:
                    content = candidate
                    break
            if content is not None:
                break
    if content is None:
        raise RuntimeError('could not construct the tokenizer-exact 2,048-token retrieval prompt')
    prompt = encode(content)

    orders = [['strata', 'ninfer'], ['ninfer', 'strata'],
              ['strata', 'ninfer'], ['ninfer', 'strata']]
    env = os.environ.copy()
    env.update({'STRATA_PREFILL_CPU_SHARE': '0'})
    profile = Path(args[args.index('--expert-profile') + 1])
    models = [Path(args[args.index(flag) + 1]) for flag in ('--native', '--ple-gguf')]
    blocks, progress = [], output / 'progress.json'
    for block_index, order in enumerate(orders):
        block = {'block': block_index + 1, 'order': order, 'arms': []}
        for backend in order:
            arm_args = args.copy()
            arm_args[arm_args.index('--expert-backend') + 1] = backend
            if backend == 'ninfer':
                arm_args.append('--expert-backend-strict')
            log = output / f'block-{block_index + 1}-{backend}.log'
            engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
            try:
                info = dict(engine.info)
                warm = measure(engine, prompt, 8, tokenizer, validate=False)
                measured = measure(engine, prompt, 16, tokenizer, validate=True)
                block['arms'].append({'backend': backend,
                                      'warmup': {'generated_tokens': warm['generated_tokens'],
                                                 'finish': warm['finish']},
                                      'measured': measured, 'engine_info': info,
                                      'log': log.name})
                progress.write_text(json.dumps({'status': 'in_progress',
                                                'prompt_tokens': len(prompt),
                                                'context_tokens': 4096,
                                                'blocks': blocks + [block]}, indent=2) + '\n')
            finally:
                engine.close()
        blocks.append(block)

    pairs = []
    metrics = {'decode_tps_gain_pct': [], 'prompt_tps_gain_pct': [],
               'ttft_reduction_pct': [], 'client_time_reduction_pct': []}
    for block in blocks:
        by_backend = {arm['backend']: arm['measured'] for arm in block['arms']}
        s, n = by_backend['strata'], by_backend['ninfer']
        metrics['decode_tps_gain_pct'].append((n['decode_tps'] / s['decode_tps'] - 1) * 100)
        metrics['prompt_tps_gain_pct'].append((n['prompt_tps'] / s['prompt_tps'] - 1) * 100)
        metrics['ttft_reduction_pct'].append((1 - n['client_first_token_ms'] / s['client_first_token_ms']) * 100)
        metrics['client_time_reduction_pct'].append((1 - n['client_total_ms'] / s['client_total_ms']) * 100)
        pairs.append({'block': block['block'], 'tokens_equal': s['token_ids'] == n['token_ids'],
                      'quality_pass_both': s['quality_pass'] and n['quality_pass'],
                      'answers': [s['answer'], n['answer']],
                      'generated_counts': [s['generated_tokens'], n['generated_tokens']],
                      'expert_hits': [s['expert_hits'], n['expert_hits']],
                      'expert_lookups': [s['expert_lookups'], n['expert_lookups']]})
    summary = {name: {'pair_effects_pct': values,
                      'paired_median_pct': statistics.median(values),
                      'paired_bootstrap_95_pct': bootstrap_median(values)}
               for name, values in metrics.items()}
    result = {
        'date': time.strftime('%Y-%m-%d'), 'hardware': 'Jetson Orin AGX, SM87, CUDA 12.6',
        'task': 'retrieve active ticket among closed-ticket distractors',
        'expected_answer': EXPECTED, 'prompt_tokens': len(prompt),
        'context_tokens': 4096, 'prompt_token_ids_sha256': hashlib.sha256(
            json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
        'prompt_content_sha256': hashlib.sha256(content.encode()).hexdigest(),
        'max_new': 16, 'temperature': 0, 'warmup_tokens': 8,
        'accepted_prefix_trace': False, 'state_hash': False,
        'identity': {'binary_sha256': file_sha256(Path(executable)),
                     'profile_sha256': file_sha256(profile), 'profile': profile.name,
                     'model_shards': [{'name': p.name, 'bytes': p.stat().st_size,
                                       'sha256': ['e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad',
                                                  '316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113'][i]}
                                      for i, p in enumerate(models)],
                     'runtime_options': {'prefill': args[args.index('--prefill') + 1],
                                         'spec': args[args.index('--spec') + 1],
                                         'prompt_cache': args[args.index('--prompt-cache') + 1],
                                         'prefill_cpu_share': 0}},
        'orders': orders, 'blocks': blocks, 'paired_quality': pairs, 'summary': summary,
        'status': ('complete_quality_pass' if all(
            p['tokens_equal'] and p['quality_pass_both'] for p in pairs
        ) else 'complete_quality_failed'),
        'limits': ['four-pair fixed-balanced screen; not a randomized confirmation',
                   'dynamic clocks; no clock controls', 'EMC readback denied',
                   'energy not measured', 'sequential client-side timing']}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    progress.unlink(missing_ok=True)
    print(json.dumps({'paired_quality': pairs, 'summary': summary, 'status': result['status']}, indent=2))
    return 0 if result['status'] == 'complete_quality_pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
