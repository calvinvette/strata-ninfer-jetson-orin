"""Repeat one file-tier mode on the same request to diagnose state instability."""
import argparse
import json
from pathlib import Path
import threading

from file_tier_transfer_parity import (
    ROOT, child_env, exact_prompt, load_tokenizer, state_hashes,
    StrataEngine, ChatTemplate,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('mapped', 'pread'), required=True)
    parser.add_argument('--prompt-tokens', type=int, default=512)
    parser.add_argument('--generated-tokens', type=int, default=64)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    tokenizer = load_tokenizer(Path(cfg['tokenizer']))
    template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    render = lambda text: tokenizer.encode(
        template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
    prompt_text = exact_prompt(args.prompt_tokens, render)
    prompt = render(prompt_text)
    if len(prompt) != args.prompt_tokens:
        raise ValueError(f'formatted prompt has {len(prompt)} tokens, expected {args.prompt_tokens}')

    engine_args = list(cfg['args'])
    for key, value in (('--max-context', str(max(args.prompt_tokens + args.generated_tokens, 8192))),
                       ('--prompt-cache', '6')):
        if key in engine_args:
            engine_args[engine_args.index(key) + 1] = value
        else:
            engine_args.extend([key, value])
    io_prefetch = '0' if args.mode == 'mapped' else '1'
    rows = []
    for repeat in range(2):
        log = args.output / f'{args.mode}-{repeat}.log'
        env = child_env(cfg)
        env.update({'STRATA_STAGE_PIN': '0', 'STRATA_STATE_HASH': '1',
                    'STRATA_MTP_BATCH': '1', 'STRATA_PREFILL_CPU_SHARE': '0',
                    'STRATA_INTEGRATION_TRACE': '1', 'STRATA_IO_PREFETCH': io_prefetch,
                    'STRATA_IO_PF_THREADS': '8', 'STRATA_IO_PF_STAGE': '0', 'STRATA_IO_STATS': '1'})
        engine = StrataEngine(str(args.engine.resolve()), engine_args, cwd=cfg.get('cwd'), log=str(log), env=env)
        try:
            ids = [token for token in engine.generate(prompt, args.generated_tokens,
                   {'temperature': 0}, threading.Event()) if token is not None]
            usage = dict(engine.last)
        finally:
            engine.close()
        rows.append({'repeat': repeat, 'token_ids': ids, 'usage': usage,
                     'state': state_hashes(log)})
    equal = rows[0]['token_ids'] == rows[1]['token_ids'] and rows[0]['state'] == rows[1]['state']
    result = {'mode': args.mode, 'prompt_tokens': len(prompt), 'generated_tokens': args.generated_tokens,
              'engine_args': engine_args, 'repeats': rows, 'token_ids_equal': rows[0]['token_ids'] == rows[1]['token_ids'],
              'persistent_state_equal': rows[0]['state'] == rows[1]['state'], 'passed': equal}
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    if not equal:
        raise AssertionError('same-mode repeated request differs in output tokens or persistent state')
    print('PASS: same-mode token IDs and persistent state match')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
