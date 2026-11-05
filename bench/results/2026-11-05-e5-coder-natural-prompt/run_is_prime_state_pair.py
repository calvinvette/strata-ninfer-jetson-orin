#!/usr/bin/env python3
"""Run a held-out Coder task through Strata and strict NInfer and compare state."""
from __future__ import annotations

import hashlib
import ast
import json
import os
import re
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer
from tools.integration.pool_worker_screen import read_accepted_prefix_trace, read_state_hashes

BASE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
TASK = ('Write a Python function named is_prime(n) that returns True exactly when n is a prime integer. '
        'Handle integers less than 2 correctly. Output only the function definition, with no explanation.')
CASES = {-7: False, 0: False, 1: False, 2: True, 3: True, 4: False, 9: False,
         25: False, 97: True, 121: False, 997: True}


def extract_function(text: str) -> str:
    text = text.replace('```python', '').replace('```', '').strip()
    match = re.search(r'(?ms)^def is_prime\s*\(.*?(?=^\S|\Z)', text)
    if not match:
        raise RuntimeError('generated response has no top-level is_prime definition')
    return match.group(0).strip()


def compile_generated_function(source: str):
    tree = ast.parse(source)
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.If, ast.Assign,
               ast.Return, ast.Compare, ast.Name, ast.Load, ast.Constant,
               ast.BinOp, ast.Mod, ast.Eq, ast.Lt, ast.Gt, ast.GtE, ast.LtE,
               ast.While, ast.AugAssign, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv,
               ast.USub, ast.UAdd, ast.Pass, ast.Store)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef) or tree.body[0].name != 'is_prime':
        raise RuntimeError('generated source must contain only the is_prime definition')
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise RuntimeError('generated source uses syntax outside the safe arithmetic subset')
    namespace: dict[str, object] = {'__builtins__': {}}
    exec(compile(tree, '<generated-is-prime>', 'exec'), namespace)
    return namespace['is_prime']


def compare_arms(left: dict, right: dict) -> dict:
    def endpoint_states(arm: dict) -> dict[int, dict]:
        endpoint = 0
        states = {}
        flattened = []
        for record in arm['accepted_prefix']:
            endpoint += record['committed']
            flattened.extend(record['token_ids'])
            states[endpoint] = record['state']
        if flattened != arm['token_ids']:
            raise RuntimeError(f"{arm['backend']}: accepted-prefix trace tokens do not match stream")
        return states

    left_states, right_states = endpoint_states(left), endpoint_states(right)
    shared = sorted(set(left_states) & set(right_states))
    changed = {position: [key for key in left_states[position]
                          if left_states[position][key] != right_states[position][key]]
               for position in shared}
    first_full = next((position for position in shared if changed[position]), None)
    live_keys = set(left_states[shared[0]]) - {'stale'} if shared else set()
    first_live = next((position for position in shared
                       if any(left_states[position][key] != right_states[position][key]
                              for key in live_keys)), None)
    return {
        'tokens_equal': left['token_ids'] == right['token_ids'],
        'task_passes_both': left['cases_pass'] and right['cases_pass'],
        'accepted_prefix_count': [len(left['accepted_prefix']), len(right['accepted_prefix'])],
        'accepted_prefix_token_totals': [len(left['token_ids']), len(right['token_ids'])],
        'shared_state_endpoints': len(shared),
        'first_full_state_difference_token': first_full,
        'first_full_state_difference_fields': changed.get(first_full, []),
        'first_non_stale_state_difference_token': first_live,
        'shared_endpoints_equal_full_state': sum(not changed[pos] for pos in shared),
        'shared_endpoints_equal_excluding_page_tail_stale_kv': sum(
            not any(key != 'stale' for key in changed[pos]) for pos in shared),
        'final_state_equal': left['final_state'] == right['final_state'],
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
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
    env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_STATE_HASH': '1',
                'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_MTP_BATCH': '1'})
    result = {'task': TASK, 'cases': CASES, 'prompt_tokens': len(prompt),
              'max_new': 128, 'temperature': 0, 'arms': []}
    profile_path = Path(args[args.index('--expert-profile') + 1])
    model_paths = [Path(args[args.index(flag) + 1]) for flag in ('--native', '--ple-gguf')]
    result['identity'] = {
        'binary_sha256': file_sha256(Path(executable)),
        'profile_sha256': file_sha256(profile_path),
        'model_shards': [{'name': path.name, 'bytes': path.stat().st_size}
                         for path in model_paths],
        'runtime_options': {'expert_cache_arg': args[args.index('--expert-cache') + 1],
                            'max_context': args[args.index('--max-context') + 1],
                            'prefill': args[args.index('--prefill') + 1],
                            'spec': args[args.index('--spec') + 1],
                            'prompt_cache': args[args.index('--prompt-cache') + 1],
                            'expert_profile': profile_path.name,
                            'prefill_cpu_share': 0,
                            'adaptive_swaps': 'inherited profile; see command in supervisor'}
    }
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        log = out / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            ids = [int(value) for value in engine.generate(prompt, 128,
                                                           {'temperature': 0}, threading.Event())
                   if value is not None]
            text = tokenizer.decode(ids)
            function = extract_function(text)
            is_prime = compile_generated_function(function)
            actual = {n: bool(is_prime(n)) for n in CASES}
            expected = {str(n): value for n, value in CASES.items()}
            actual_json = {str(n): value for n, value in actual.items()}
            trace = read_accepted_prefix_trace(log)
            hashes = read_state_hashes(log)
            if not ids or not trace or not hashes:
                raise RuntimeError(f'{backend}: missing token, accepted-prefix or final-state evidence')
            result['arms'].append({'backend': backend, 'token_ids': ids,
                                   'token_sha256': hashlib.sha256(bytes().join(
                                       int(v).to_bytes(4, 'little') for v in ids)).hexdigest(),
                                   'text': text, 'function': function,
                                   'case_results': actual_json, 'cases_pass': actual_json == expected,
                                   'finish': engine.last, 'accepted_prefix': trace,
                                   'final_state': hashes[-1], 'log': log.name})
        finally:
            engine.close()
    left, right = result['arms']
    result['comparison'] = compare_arms(left, right)
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['comparison'], indent=2))
    return 0 if result['comparison']['task_passes_both'] else 2


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--analyze':
        path = Path(sys.argv[2])
        result = json.loads(path.read_text())
        result['comparison'] = compare_arms(*result['arms'])
        path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result['comparison'], indent=2))
        raise SystemExit(0)
    raise SystemExit(main())
