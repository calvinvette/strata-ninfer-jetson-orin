"""Run one short Q2_0 request with automatic cache sizing and retain its holds."""
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from file_tier_transfer_parity import ChatTemplate, StrataEngine, exact_prompt, load_tokenizer
from owner_observations import summarize

CONFIG = ROOT / 'bench/results/2026-10-12-phase3-q2-cache-context-state/campaign/base-config.json'
OUT = Path(sys.argv[1]).resolve()


def replace(args, key, value):
    if key not in args:
        args.extend([key, str(value)])
    else:
        args[args.index(key) + 1] = str(value)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    config = json.loads(CONFIG.read_text())
    args = list(config['args'])
    replace(args, '--expert-cache', 'auto')
    replace(args, '--max-context', 8192)
    replace(args, '--prompt-cache', 0)
    env = dict(config.get('env', {}))
    env.update({'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_HASH': '1'})
    tokenizer = load_tokenizer(Path(config['tokenizer']))
    template_path = Path(config['tokenizer']) / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    render = lambda text: tokenizer.encode(
        template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
    prompt = render(exact_prompt(512, render))
    if len(prompt) != 512:
        raise RuntimeError(f'prepared prompt has {len(prompt)} tokens, expected 512')
    engine = StrataEngine(config['exe'], args, cwd=config.get('cwd'),
                          log=str(OUT / 'engine.log'), env=env)
    try:
        generated = [token for token in engine.generate(
            prompt, 1, {'temperature': 0}, threading.Event()) if token is not None]
        result = {
            'prompt_tokens': len(prompt),
            'prompt_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
            'generated_ids': generated,
            'engine_sha256': hashlib.sha256(Path(config['exe']).read_bytes()).hexdigest(),
            'engine_args': args,
            'engine': dict(engine.last),
            'passed': len(generated) == 1,
        }
        (OUT / 'workload.json').write_text(json.dumps(result, indent=2) + '\n')
        if not result['passed']:
            raise RuntimeError('one-token request failed')
    finally:
        engine.close()
    summary = summarize((OUT / 'engine.log').read_text().splitlines())
    (OUT / 'owner-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'generated_ids': generated,
                      'engine_sha256': result['engine_sha256'],
                      'planned_reservations': summary['planned_reservations'],
                      'owners': summary['owners']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
