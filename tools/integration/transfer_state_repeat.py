"""Repeat one file-tier mode on the same request to diagnose state instability."""
import argparse
import json
from pathlib import Path
import re
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
    parser.add_argument('--expert-cache', type=str,
                        help='override auto cache sizing for a stable same-mode residency control')
    parser.add_argument('--prompt-tokens', type=int, default=512)
    parser.add_argument('--generated-tokens', type=int, default=64)
    parser.add_argument('--no-token-graph', action='store_true',
                        help='disable the separate token-graph path (not the serving verifier graph)')
    parser.add_argument('--commit-one-token', action='store_true',
                        help='use the older verifier commit graph after one-token windows')
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
    if args.expert_cache is not None:
        if '--expert-cache' in engine_args:
            engine_args[engine_args.index('--expert-cache') + 1] = args.expert_cache
        else:
            engine_args.extend(['--expert-cache', args.expert_cache])
    if args.no_token_graph:
        engine_args.append('--no-token-graph')
    io_prefetch = '0' if args.mode == 'mapped' else '1'
    rows = []
    for repeat in range(2):
        log = args.output / f'{args.mode}-{repeat}.log'
        env = child_env(cfg)
        env.update({'STRATA_STAGE_PIN': '0', 'STRATA_STATE_HASH': '1',
                    'STRATA_STATE_HASH_GDN': '1',
                    'STRATA_MTP_BATCH': '1', 'STRATA_PREFILL_CPU_SHARE': '0',
                    'STRATA_INTEGRATION_TRACE': '1', 'STRATA_IO_PREFETCH': io_prefetch,
                    'STRATA_IO_PF_THREADS': '8', 'STRATA_IO_PF_STAGE': '0', 'STRATA_IO_STATS': '1'})
        if args.commit_one_token:
            env['STRATA_ONE_TOKEN_COMMIT'] = '0'
        engine = StrataEngine(str(args.engine.resolve()), engine_args, cwd=cfg.get('cwd'), log=str(log), env=env)
        try:
            ids = [token for token in engine.generate(prompt, args.generated_tokens,
                   {'temperature': 0}, threading.Event()) if token is not None]
            usage = dict(engine.last)
        finally:
            engine.close()
        lines = log.read_text(errors='replace').splitlines()
        gdn_line = next((line for line in lines if 'STATE_HASH_GDN ' in line), '')
        prefill_gdn_line = next((line for line in lines if 'prefill: GDN_HASH ' in line), '')
        gdn_match = re.search(r'STATE_HASH_GDN\s+([0-9a-fA-F ]+)', gdn_line)
        prefill_match = re.search(r'prefill: GDN_HASH\s+([0-9a-fA-F ]+)', prefill_gdn_line)
        rows.append({'repeat': repeat, 'token_ids': ids, 'usage': usage,
                     'state': state_hashes(log),
                     'gdn_prefill_layer_hashes16': prefill_match.group(1).split() if prefill_match else None,
                     'gdn_layer_hashes16': gdn_match.group(1).split() if gdn_match else None})
    equal = rows[0]['token_ids'] == rows[1]['token_ids'] and rows[0]['state'] == rows[1]['state']
    prefill_gdn_equal = (rows[0]['gdn_prefill_layer_hashes16'] ==
                         rows[1]['gdn_prefill_layer_hashes16'])
    result = {'mode': args.mode, 'prompt_tokens': len(prompt), 'generated_tokens': args.generated_tokens,
              'engine_args': engine_args, 'expert_cache_override': args.expert_cache,
              'prefill_gdn_equal': prefill_gdn_equal, 'no_token_graph': args.no_token_graph,
              'legacy_one_token_commit': args.commit_one_token,
              'repeats': rows, 'token_ids_equal': rows[0]['token_ids'] == rows[1]['token_ids'],
              'persistent_state_equal': rows[0]['state'] == rows[1]['state'], 'passed': equal}
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    if not equal:
        raise AssertionError('same-mode repeated request differs in output tokens or persistent state')
    print('PASS: same-mode token IDs and persistent state match')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
