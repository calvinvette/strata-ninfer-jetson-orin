"""Run one Q2_0 accepted-prefix state cell for cache/context diagnosis."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from file_tier_transfer_parity import load_tokenizer, ChatTemplate, exact_prompt, StrataEngine


def replace(args, key, value):
    if key not in args:
        args.extend([key, str(value)])
    else:
        index = args.index(key)
        args[index + 1] = str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=int, required=True)
    parser.add_argument('--context', type=int, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    config = json.loads(args.config.read_text())
    tokenizer = load_tokenizer(Path(config['tokenizer']))
    template_path = Path(config['tokenizer']) / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    render = lambda text: tokenizer.encode(
        template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
    full_prompt = render(exact_prompt(512, render))
    if len(full_prompt) != 512:
        raise RuntimeError(f'prepared prompt has {len(full_prompt)} tokens, expected 512')
    prompt = full_prompt[:511]

    engine_args = list(config['args'])
    replace(engine_args, '--expert-cache', args.cache)
    replace(engine_args, '--max-context', args.context)
    replace(engine_args, '--prompt-cache', 6)
    env = dict(config.get('env', {}))
    env.pop('LD_PRELOAD', None)
    dump = (ROOT / 'build/integration/q2-cache-context-state' / output.name / 'gdn-L511.bin')
    dump.parent.mkdir(parents=True, exist_ok=True)
    env.update({
        'STRATA_STAGE_PIN': '0',
        'STRATA_PREFILL_CPU_SHARE': '0',
        'STRATA_INTEGRATION_TRACE': '1',
        'STRATA_STATE_HASH': '1',
        'STRATA_STATE_HASH_GDN': '1',
        'STRATA_STATE_DUMP_GDN': str(dump.resolve()),
        'STRATA_STATE_DUMP_GDN_AT': '511',
    })
    engine = StrataEngine(str(args.engine.resolve()), engine_args,
                          cwd=config.get('cwd'), log=str((output / 'engine.log').resolve()), env=env)
    try:
        generated = [token for token in engine.generate(prompt, 1, {'temperature': 0}, threading.Event())
                     if token is not None]
        result = {
            'prompt_tokens': len(prompt),
            'prompt_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
            'generated_ids': generated,
            'usage': dict(engine.last),
            'engine_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(),
            'engine_args': engine_args,
            'gdn_dump_path': str(dump.resolve()),
            'gdn_dump_bytes': dump.stat().st_size if dump.exists() else None,
            'gdn_dump_sha256': hashlib.sha256(dump.read_bytes()).hexdigest() if dump.exists() else None,
            'passed': len(generated) == 1 and dump.exists(),
        }
        (output / 'workload.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({key: result[key] for key in
                          ('prompt_tokens', 'prompt_sha256', 'generated_ids', 'usage', 'gdn_dump_sha256', 'passed')}),
              flush=True)
        if not result['passed']:
            raise RuntimeError('request or accepted-prefix GDN dump failed')
    finally:
        engine.close()


if __name__ == '__main__':
    main()
