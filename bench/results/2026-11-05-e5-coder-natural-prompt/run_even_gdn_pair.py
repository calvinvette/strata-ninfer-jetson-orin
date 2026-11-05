"""Capture first-token recurrent state for the held-out is_even task."""
import hashlib
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from serve.server import StrataEngine
from serve.frontend import ChatTemplate
from tools.conversation_cache_parity import load_tokenizer

BASE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'


def main() -> int:
    command = json.loads(BASE.read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    args[args.index('--max-new') + 1] = '1'
    del args[args.index('--tokens'):args.index('--tokens') + 2]

    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    prompt_text = ('Write a Python function named is_even(n) that returns True '
                   'exactly when the integer n is evenly divisible by 2. Output '
                   'only Python code defining is_even.')
    prompt = tokenizer.encode(template.render([{'role': 'user', 'content': prompt_text}],
                                               enable_thinking=False), parse_special=True)
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_STATE_HASH': '1',
                'STRATA_STATE_HASH_GDN': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_DUMP_GDN_AT': str(len(prompt))})
    arms = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        dump = output / f'{backend}.gdn.bin'
        arm_env = env.copy()
        arm_env['STRATA_STATE_DUMP_GDN'] = str(dump.resolve())
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=arm_env)
        try:
            ids = [int(value) for value in engine.generate(prompt, 1, {'temperature': 0},
                                                            threading.Event()) if value is not None]
            arms.append({'backend': backend, 'token_ids': ids, 'finish': engine.last,
                         'dump_path': dump.name,
                         'dump_sha256': hashlib.sha256(dump.read_bytes()).hexdigest(),
                         'log_path': log.name})
        finally:
            engine.close()
    result = {'prompt_text': prompt_text, 'prompt_tokens': len(prompt),
              'dump_state_length': len(prompt), 'temperature': 0, 'arms': arms,
              'token_ids_equal': arms[0]['token_ids'] == arms[1]['token_ids']}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'arms'}, indent=2))
    for arm in arms:
        print(arm['backend'], arm['token_ids'], arm['dump_sha256'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
