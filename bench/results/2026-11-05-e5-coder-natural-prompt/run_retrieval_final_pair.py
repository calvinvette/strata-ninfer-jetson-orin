#!/usr/bin/env python3
"""Compare final-only state for a tokenizer-exact long-context retrieval task."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
EXPECTED = '73192'
TARGET_PROMPT = 2048
PREFIX = 'Archived closed tickets: '
FILLER = 'ticket closed code 11804; status resolved. '
SUFFIX = (
    '\nACTIVE TICKET: code 73192; status open. '
    'Question: return the code for the active ticket using digits only.'
)
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration'),
                str(ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt')]
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer
from run_is_prime_state_pair import file_sha256, read_complete_final_state

BASE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'


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
    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')

    def encode_content(content: str) -> list[int]:
        rendered = template.render([{'role': 'user', 'content': content}], enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    low, high, content = 0, TARGET_PROMPT, None
    while low <= high:
        count = (low + high) // 2
        candidate = PREFIX + FILLER * count + SUFFIX
        actual = len(encode_content(candidate))
        if actual == TARGET_PROMPT:
            content = candidate
            break
        if actual < TARGET_PROMPT:
            low = count + 1
        else:
            high = count - 1
    if content is None:
        raise RuntimeError('could not construct exact 2,048-token retrieval prompt')
    prompt = encode_content(content)
    if len(prompt) != TARGET_PROMPT:
        raise RuntimeError(f'prompt token count changed: {len(prompt)}')

    env = os.environ.copy()
    env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_STATE_HASH': '1'})
    profile = Path(args[args.index('--expert-profile') + 1])
    models = [Path(args[args.index(flag) + 1]) for flag in ('--native', '--ple-gguf')]
    result = {
        'task': 'retrieve open active ticket code among repeated closed-ticket distractors',
        'expected_answer': EXPECTED, 'prompt_tokens': len(prompt), 'context_reservation': 4096,
        'prompt_token_ids_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
        'prompt_content_sha256': hashlib.sha256(content.encode()).hexdigest(),
        'max_new': 16, 'temperature': 0, 'accepted_prefix_capture': False,
        'identity': {
            'binary_sha256': file_sha256(Path(executable)), 'profile_sha256': file_sha256(profile),
            'expert_profile': profile.name,
            'model_shards': [{'name': p.name, 'bytes': p.stat().st_size} for p in models],
            'runtime_options': {'expert_cache_arg': args[args.index('--expert-cache') + 1],
                                'prefill': args[args.index('--prefill') + 1], 'context': '4096',
                                'spec': args[args.index('--spec') + 1], 'prompt_cache': args[args.index('--prompt-cache') + 1],
                                'prefill_cpu_share': 0}
        }, 'arms': []
    }
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            ids = [int(value) for value in engine.generate(prompt, 16,
                                                           {'temperature': 0}, threading.Event())
                   if value is not None]
            decoded = tokenizer.decode(ids).strip()
            answer = decoded.split('<|im_end|>', 1)[0].strip()
            result['arms'].append({'backend': backend, 'token_ids': ids,
                                   'token_ids_sha256': hashlib.sha256(b''.join(
                                       value.to_bytes(4, 'little') for value in ids)).hexdigest(),
                                   'decoded': decoded, 'answer': answer,
                                   'answer_pass': answer == EXPECTED, 'finish': engine.last,
                                   'final_state': read_complete_final_state(log), 'log': log.name})
        finally:
            engine.close()
    left, right = result['arms']
    diffs = [key for key in left['final_state'] if left['final_state'][key] != right['final_state'][key]]
    result['comparison'] = {'tokens_equal': left['token_ids'] == right['token_ids'],
                            'answer_passes_both': left['answer_pass'] and right['answer_pass'],
                            'final_state_equal': not diffs, 'final_state_difference_fields': diffs}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['comparison'], indent=2))
    return 0 if result['comparison']['answer_passes_both'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
