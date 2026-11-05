#!/usr/bin/env python3
"""Capture MoE input and weighted routes at the first observed route split."""
from __future__ import annotations

import array
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration'),
                str(ROOT / 'bench/results/2026-11-05-e6-coder-retrieval-2k'),
                str(ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt')]
from run_retrieval_perf_screen import BASE, EXPECTED, FILLER, PREFIX, ROOT, SUFFIX, measure
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer

LAYER = 16
POSITION = 2047


def parse_input_dump(path: Path) -> dict:
    data = path.read_bytes()
    header_size = 72
    result = None
    offset = 0
    while offset + header_size <= len(data):
        magic, version, layer, rows, _reserved, embd, pos0, *tokens = struct.unpack_from('<8sIIIIQq4i', data, offset)
        if magic != b'STMOINP1' or version != 1 or rows < 1 or embd < 1:
            raise ValueError(f'invalid MoE input record at offset {offset}')
        payload = rows * embd * 4
        start = offset + header_size
        if start + payload > len(data):
            raise ValueError('truncated MoE input payload')
        for row in range(rows):
            if pos0 + row == POSITION:
                values = array.array('f')
                values.frombytes(data[start + row * embd * 4:start + (row + 1) * embd * 4])
                result = {'layer': layer, 'position': POSITION, 'token_id': tokens[row],
                          'n_embd': embd, 'activation': values}
        offset = start + payload
    if offset != len(data) or result is None or result['layer'] != LAYER:
        raise ValueError('did not find the requested layer/position in MoE input dump')
    return result


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
    encode = lambda text: tokenizer.encode(template.render(
        [{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
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
    if content is None or len(encode(content)) != target:
        raise RuntimeError('could not construct exact 2,048-token retrieval prompt')
    prompt = encode(content)

    arms = []
    captures = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        route_path = output / f'{backend}-route.jsonl'
        input_path = output / f'{backend}-input.bin'
        env = os.environ.copy()
        env.update({'STRATA_RESIDENT_HEADROOM_GIB': '6', 'STRATA_PREFILL_CPU_SHARE': '0',
                    'STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER': str(LAYER),
                    'STRATA_VERIFY_DUMP_MOE_ROUTE_POSITION': str(POSITION),
                    'STRATA_VERIFY_DUMP_MOE_ROUTE_PATH': str(route_path),
                    'STRATA_VERIFY_DUMP_MOE_INPUT_LAYER': str(LAYER),
                    'STRATA_VERIFY_DUMP_MOE_INPUT_POSITION': str(POSITION),
                    'STRATA_VERIFY_DUMP_MOE_INPUT_PATH': str(input_path)})
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            row = measure(engine, prompt, 16, tokenizer, validate=True)
            route_records = [json.loads(line) for line in route_path.read_text().splitlines()[1:]]
            route = next(x for x in route_records if x['layer'] == LAYER and x['position'] == POSITION)
            activation = parse_input_dump(input_path)
            arms.append({'backend': backend, 'answer': row['answer'], 'token_ids': row['token_ids'],
                         'quality_pass': row['quality_pass'], 'route': route,
                         'activation': activation['activation'], 'token_id_at_boundary': activation['token_id'],
                         'input_file': input_path.name, 'route_file': route_path.name, 'log': log.name})
            captures.append((input_path, route_path))
        finally:
            engine.close()

    a, b = arms
    av, bv = a['activation'], b['activation']
    delta2 = sum((x - y) ** 2 for x, y in zip(av, bv))
    base2 = sum(x * x for x in av)
    route_a, route_b = a['route'], b['route']
    result = {'task': 'exact 2,048-token Coder active-ticket retrieval',
              'profile': 'static 6 GiB PCIe complement, adapt-every=0',
              'layer': LAYER, 'position': POSITION,
              'boundary_token_ids_match': a['token_id_at_boundary'] == b['token_id_at_boundary'],
              'route_expert_sets_match': set(route_a['ids']) == set(route_b['ids']),
              'route_order_match': route_a['ids'] == route_b['ids'],
              'route_weights_match_in_order': route_a['weights'] == route_b['weights'],
              'input_bitwise_match': av == bv,
              'input_relative_l2': (delta2 / base2) ** 0.5 if base2 else None,
              'input_max_abs': max(abs(x - y) for x, y in zip(av, bv)),
              'input_changed_values': sum(x != y for x, y in zip(av, bv)),
              'answers_match': a['answer'] == b['answer'] == EXPECTED,
              'token_sequences_match': a['token_ids'] == b['token_ids'],
              'arms': [{k: v for k, v in arm.items() if k != 'activation'} for arm in arms],
              'raw_inputs': [{'name': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                             for p, _ in captures],
              'raw_routes': [{'name': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                             for _, p in captures],
              'note': 'instrumented diagnostic; timing excluded; raw activation arrays stay local'}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('boundary_token_ids_match', 'route_expert_sets_match',
                                              'route_order_match', 'route_weights_match_in_order',
                                              'input_bitwise_match', 'input_relative_l2', 'input_max_abs',
                                              'input_changed_values', 'answers_match', 'token_sequences_match')},
                     indent=2))
    return 0 if result['answers_match'] and result['token_sequences_match'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
