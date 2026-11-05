#!/usr/bin/env python3
"""Capture routed expert IDs and owners across all layers of a 2K retrieval."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
RUN_DIR = ROOT / 'bench/results/2026-11-05-e6-coder-retrieval-2k'
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration'), str(RUN_DIR),
                str(ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt')]

from run_retrieval_perf_screen import BASE, FILLER, PREFIX, SUFFIX, EXPECTED, measure
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer


def main() -> int:
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
    args.extend(['--pcie-frac', '1.0', '--resident-budget-gib', '6', '--adapt-every', '0'])

    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')

    def encode(content: str) -> list[int]:
        return tokenizer.encode(template.render(
            [{'role': 'user', 'content': content}], enable_thinking=False), parse_special=True)

    target, low, high, content = 2048, 0, 2048, None
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
        raise RuntimeError('could not construct exact 2,048-token retrieval prompt')
    prompt = encode(content)
    if len(prompt) != 2048:
        raise RuntimeError(f'constructed prompt has {len(prompt)} tokens, expected 2048')

    arms = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        capture = output / f'{backend}-all-layer-routes.jsonl'
        env = os.environ.copy()
        env.update({'STRATA_RESIDENT_HEADROOM_GIB': '6',
                    'STRATA_CAPTURE_MOE_PATH': str(capture),
                    'STRATA_CAPTURE_MOE_LAYER': '-1',
                    'STRATA_CAPTURE_MOE_ROWS': '4096'})
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            row = measure(engine, prompt, 16, tokenizer, validate=True)
            parsed = [json.loads(line) for line in capture.read_text().splitlines()]
            rows = parsed[1:]
            owner_counts = Counter()
            layer_owner_counts = Counter()
            expert_owner_counts = Counter()
            for record in rows:
                for expert, owner in zip(record['ids'], record['route_kind']):
                    name = { -1: 'cpu', 0: 'resident_gpu', 1: 'pcie', 2: 'peer_gpu'}.get(owner, f'unknown_{owner}')
                    owner_counts[name] += 1
                    layer_owner_counts[(int(record['layer']), name)] += 1
                    expert_owner_counts[(int(record['layer']), int(expert), name)] += 1
            arms.append({'backend': backend, 'answer': row['answer'],
                         'token_ids': row['token_ids'], 'quality_pass': row['quality_pass'],
                         'generated_tokens': row['generated_tokens'],
                         'capture_sha256': hashlib.sha256(capture.read_bytes()).hexdigest(),
                         'captured_rows': len(rows), 'route_entries': sum(owner_counts.values()),
                         'owner_counts': dict(owner_counts),
                         'layer_owner_counts': [
                             {'layer': layer, 'owner': owner, 'routes': count}
                             for (layer, owner), count in sorted(layer_owner_counts.items())],
                         'expert_owner_counts': [
                             {'layer': layer, 'expert_id': expert, 'owner': owner, 'routes': count}
                             for (layer, expert, owner), count in sorted(expert_owner_counts.items())],
                         'engine_info': dict(engine.info), 'log': log.name,
                         'capture': capture.name})
        finally:
            engine.close()

    traces = []
    for arm in arms:
        trace_path = output / arm['capture']
        traces.append([json.loads(line) for line in trace_path.read_text().splitlines()[1:]])
    aligned = len(traces[0]) == len(traces[1]) and all(
        (a['layer'], a['position'], a['token_id']) == (b['layer'], b['position'], b['token_id'])
        for a, b in zip(*traces))
    route_set_mismatches = 0
    ordered_id_mismatches = 0
    shared_owner_mismatches = 0
    if aligned:
        for a, b in zip(*traces):
            route_set_mismatches += set(a['ids']) != set(b['ids'])
            ordered_id_mismatches += a['ids'] != b['ids']
            owner_a = dict(zip(a['ids'], a['route_kind']))
            owner_b = dict(zip(b['ids'], b['route_kind']))
            shared_owner_mismatches += any(owner_a[e] != owner_b[e] for e in owner_a.keys() & owner_b.keys())

    result = {'purpose': 'instrumented ownership diagnostic; timing excluded',
              'task': 'exact 2,048-token Coder active-ticket retrieval',
              'context_tokens': 4096, 'generated_token_budget': 16,
              'profile': 'static 6 GiB PCIe complement, adapt-every=0, six GiB headroom',
              'captured_layer': 'all', 'arms': arms,
              'route_comparison': {'row_metadata_aligned': aligned,
                                   'rows_with_different_expert_set': route_set_mismatches,
                                   'rows_with_different_ordered_ids': ordered_id_mismatches,
                                   'rows_with_owner_class_difference_for_shared_experts': shared_owner_mismatches},
              'token_sequences_match': arms[0]['token_ids'] == arms[1]['token_ids'],
              'answers_match': arms[0]['answer'] == arms[1]['answer'] == '73192'}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('purpose', 'token_sequences_match', 'answers_match')}, indent=2))
    for arm in arms:
        print(json.dumps({'backend': arm['backend'], 'captured_rows': arm['captured_rows'],
                          'route_entries': arm['route_entries'], 'owner_counts': arm['owner_counts'],
                          'quality_pass': arm['quality_pass']}))
    return 0 if result['token_sequences_match'] and result['answers_match'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
