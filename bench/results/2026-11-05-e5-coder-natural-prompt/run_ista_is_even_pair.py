"""Run the held-out is_even oracle on the actual ISTA IQ3_S model."""
import json
import os
import re
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from serve.server import StrataEngine
from serve.frontend import ChatTemplate
from tools.conversation_cache_parity import load_tokenizer
from tools.integration.pool_worker_screen import read_accepted_prefix_trace


def evaluate(text: str) -> dict:
    namespace = {}
    try:
        exec(compile(text, '<generated>', 'exec'), {'__builtins__': __builtins__}, namespace)
        fn = namespace.get('is_even')
        if not callable(fn):
            raise AssertionError('response does not define is_even')
        cases = [(0, True), (1, False), (2, True), (3, False), (-2, True), (-3, False)]
        rows = [{'input': value, 'expected': expected, 'actual': fn(value)}
                for value, expected in cases]
        for row in rows:
            row['passed'] = row['actual'] is row['expected']
        return {'passed': all(row['passed'] for row in rows), 'cases': rows}
    except Exception as exc:
        return {'passed': False, 'error': f'{type(exc).__name__}: {exc}'}


def main() -> int:
    command = json.loads((ROOT / 'bench/results/2026-11-05-e4-iq4xs-iq4nl/service-ista-strict-matching-pack/result.json').read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    if len(sys.argv) > 2:
        args[args.index('--expert-profile') + 1] = str(Path(sys.argv[2]).resolve())
    args[args.index('--max-new') + 1] = '64'
    if '--expert-backend-strict' in args:
        args.remove('--expert-backend-strict')
    args[args.index('--spec') + 1] = '2'
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/iq3-s-pack/tokenizer')
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
                'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1'})
    arms = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            ids = [int(value) for value in engine.generate(prompt, 64, {'temperature': 0},
                                                            threading.Event()) if value is not None]
            raw_text = tokenizer.decode(ids).strip()
            code = raw_text.split('<|im_end|>', 1)[0].strip()
            if code.startswith('```'):
                code = code.partition('\n')[2]
                if code.rstrip().endswith('```'):
                    code = code.rstrip()[:-3].rstrip()
            hashes = [dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
                      for line in log.read_text(errors='replace').splitlines()
                      if line.startswith('strata serve: STATE_HASH L=')]
            trace = read_accepted_prefix_trace(log)
            arms.append({'backend': backend, 'token_ids': ids, 'generated_code': code,
                         'quality': evaluate(code), 'finish': engine.last,
                         'final_state': hashes[-1] if hashes else None,
                         'accepted_prefix_entries': len(trace),
                         'accepted_prefix_tokens': [t for row in trace for t in row['token_ids']]})
        finally:
            engine.close()
    result = {'prompt_text': prompt_text, 'prompt_tokens': len(prompt), 'max_new': 64,
              'model_variant': 'ISTA-DASLab Qwen3.8-Flash-Next IQ3_S GGUF',
              'source_command_result': '2026-11-05-e4-iq4xs-iq4nl/service-ista-strict-matching-pack/result.json',
              'temperature': 0, 'arms': arms,
              'both_answer_oracles_passed': all(row['quality']['passed'] for row in arms),
              'token_ids_equal': arms[0]['token_ids'] == arms[1]['token_ids'],
              'final_state_equal': arms[0]['final_state'] == arms[1]['final_state'],
              'accepted_prefix_tokens_equal': arms[0]['accepted_prefix_tokens'] == arms[1]['accepted_prefix_tokens']}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'arms'}, indent=2))
    for arm in arms:
        print(arm['backend'], arm['quality'], arm['finish'])
    return 0 if result['both_answer_oracles_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
