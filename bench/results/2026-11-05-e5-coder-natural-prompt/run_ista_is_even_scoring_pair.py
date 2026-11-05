#!/usr/bin/env python3
"""Teacher-force the held-out ISTA IQ3_S is_even answer through both backends."""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration'),
                str(ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt')]
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer
from run_is_prime_state_pair import file_sha256


def parse_scores(path: Path) -> list[dict]:
    rows = []
    for raw in path.read_text().splitlines():
        cols = raw.split('\t')
        if len(cols) < 8:
            raise ValueError(f'{path}: malformed score row: {raw!r}')
        topk = []
        for item in cols[8:]:
            token, logp = item.split(':', 1)
            topk.append({'token_id': int(token), 'logprob': float(logp)})
        rows.append({'position': int(cols[0]), 'target_id': int(cols[1]),
                     'target_logprob': float(cols[2]), 'top1_id': int(cols[3]),
                     'top1_logprob': float(cols[4]), 'target_is_top1': bool(int(cols[5])),
                     'eot_logprob': float(cols[6]), 'without_eot_logprob': float(cols[7]),
                     'topk': topk})
    return rows


def summarize(left: list[dict], right: list[dict], positions: list[int]) -> dict:
    a = {row['position']: row for row in left}
    b = {row['position']: row for row in right}
    if set(a) != set(b):
        raise ValueError('backend score positions differ')
    selected = [(a[p], b[p]) for p in positions]
    if not selected:
        raise ValueError('no target answer positions selected')
    deltas = [n['target_logprob'] - s['target_logprob'] for s, n in selected]
    top1_equal = [s['top1_id'] == n['top1_id'] for s, n in selected]
    overlap10 = []
    for s, n in selected:
        si = {row['token_id'] for row in s['topk'][:10]}
        ni = {row['token_id'] for row in n['topk'][:10]}
        overlap10.append(len(si & ni) / 10.0)
    strata_sum = math.fsum(s['target_logprob'] for s, _ in selected)
    ninfer_sum = math.fsum(n['target_logprob'] for _, n in selected)
    count = len(selected)
    return {'scored_answer_tokens': count,
            'strata_sum_logprob': strata_sum, 'ninfer_sum_logprob': ninfer_sum,
            'strata_mean_logprob': strata_sum / count, 'ninfer_mean_logprob': ninfer_sum / count,
            'strata_perplexity': math.exp(-strata_sum / count),
            'ninfer_perplexity': math.exp(-ninfer_sum / count),
            'ninfer_minus_strata_total_logprob': ninfer_sum - strata_sum,
            'mean_target_logprob_delta_ninfer_minus_strata': statistics.mean(deltas),
            'median_abs_target_logprob_delta': statistics.median(map(abs, deltas)),
            'max_abs_target_logprob_delta': max(map(abs, deltas)),
            'top1_agreement_fraction': statistics.mean(top1_equal),
            'mean_top10_overlap_fraction': statistics.mean(overlap10),
            'per_answer_token': [{'position': s['position'], 'target_id': s['target_id'],
                                  'strata_logprob': s['target_logprob'],
                                  'ninfer_logprob': n['target_logprob'],
                                  'delta': n['target_logprob'] - s['target_logprob'],
                                  'top1_equal': s['top1_id'] == n['top1_id'],
                                  'top10_overlap': int(len(
                                      {r['token_id'] for r in s['topk'][:10]} &
                                      {r['token_id'] for r in n['topk'][:10]}))}
                                 for s, n in selected]}


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_command = json.loads((ROOT / 'bench/results/2026-11-05-e4-iq4xs-iq4nl/service-ista-strict-matching-pack/result.json').read_text())['command']
    index = next(i for i, item in enumerate(source_command)
                 if item.endswith('/strata') or item == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / source_command[index]).resolve())
    args = source_command[index + 1:].copy()
    if '--expert-backend-strict' in args:
        args.remove('--expert-backend-strict')
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    args[args.index('--max-new') + 1] = '1'
    args[args.index('--max-context') + 1] = '512'
    if '--short-read' in args:
        args[args.index('--short-read') + 1] = '512'
    else:
        args += ['--short-read', '512']

    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/iq3-s-pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    source_results = json.loads((ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/ista-is-even-run/results.json').read_text())
    task = source_results['prompt_text']
    generation_prompt = tokenizer.encode(
        template.render([{'role': 'user', 'content': task}], enable_thinking=False),
        parse_special=True)
    target_ids = source_results['arms'][0]['token_ids']
    if target_ids != source_results['arms'][1]['token_ids']:
        raise RuntimeError('source Strata/NInfer answer tokens are not equal')
    full_ids = generation_prompt + [int(token) for token in target_ids]
    profile = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(args[args.index('--expert-profile') + 1])
    cache_arg = sys.argv[3] if len(sys.argv) > 3 else args[args.index('--expert-cache') + 1]
    args[args.index('--expert-profile') + 1] = str(profile)
    args[args.index('--expert-cache') + 1] = cache_arg
    model_shards = json.loads((ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/ista-is-even/results.json').read_text())['model_shards']
    env = os.environ.copy()
    env['STRATA_PREFILL_CPU_SHARE'] = '0'
    env['STRATA_LOGPOS_TOPK'] = '20'
    arms = []
    score_rows = {}
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        score_path = output / f'{backend}.logpos'
        arm_env = dict(env, STRATA_LOGPOS=str(score_path))
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=arm_env)
        try:
            generated = [int(x) for x in engine.generate(full_ids, 1,
                                                          {'temperature': 0}, threading.Event())
                         if x is not None]
            rows = parse_scores(score_path)
            score_rows[backend] = rows
            arms.append({'backend': backend, 'input_token_count': len(full_ids),
                         'generated_probe_token_ids': generated, 'score_row_count': len(rows),
                         'score_file_sha256': hashlib.sha256(score_path.read_bytes()).hexdigest(),
                         'finish': dict(engine.last), 'log': log.name})
        finally:
            engine.close()
    if len(score_rows['strata']) != len(full_ids) - 1 or len(score_rows['ninfer']) != len(full_ids) - 1:
        raise RuntimeError(f"score coverage incomplete: input={len(full_ids)}, "
                           f"Strata={len(score_rows['strata'])}, NInfer={len(score_rows['ninfer'])}")
    for backend, rows in score_rows.items():
        for row in rows:
            if row['target_id'] != full_ids[row['position'] + 1]:
                raise RuntimeError(f'{backend}: target mismatch at position {row["position"]}')
    answer_positions = list(range(len(generation_prompt) - 1, len(full_ids) - 1))
    summary = summarize(score_rows['strata'], score_rows['ninfer'], answer_positions)
    result = {'date': '2026-11-05', 'hardware': 'Jetson Orin AGX, CUDA 12.6',
              'task': 'teacher-force the held-out is_even answer on the actual ISTA IQ3_S model',
              'target_answer_tokens': len(target_ids), 'prompt_tokens': len(generation_prompt),
              'input_tokens': len(full_ids), 'answer_positions': answer_positions,
              'prompt_token_ids_sha256': hashlib.sha256(
                  json.dumps(generation_prompt, separators=(',', ':')).encode()).hexdigest(),
              'answer_token_ids_sha256': hashlib.sha256(
                  b''.join(int(t).to_bytes(4, 'little') for t in target_ids)).hexdigest(),
              'binary_sha256': file_sha256(Path(executable)),
              'expert_profile_sha256': file_sha256(profile),
              'model_shards': model_shards,
              'runtime': {'expert_profile': profile.name,
                          'expert_cache_arg': args[args.index('--expert-cache') + 1],
                          'context': 512, 'short_read': 512,
                          'expert_backend': ['strata', 'ninfer-strict'],
                          'mtp_window': args[args.index('--spec') + 1],
                          'prefill_cpu_share': 0, 'logpos_topk': 20,
                          'timing_used': False},
              'arms': arms, 'score': summary,
              'coverage': {'all_prefill_targets_scored': len(generation_prompt + target_ids) - 1,
                           'answer_targets_scored': len(answer_positions),
                           'all_target_ids_verified_against_input': True}}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'score': {k: v for k, v in summary.items() if k != 'per_answer_token'},
                      'coverage': result['coverage']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
