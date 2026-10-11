"""Probe whether a rejected MTP suffix affects a same-engine continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import STATE_KEYS, args_for, parse_hashes
from conversation_cache_parity import load_tokenizer, require
from pool_worker_screen import read_accepted_prefix_trace
from prepare_controls import exact_prompt
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prompt-tokens', type=int, default=512)
    parser.add_argument('--initial-tokens', type=int, default=8)
    parser.add_argument('--continuation-tokens', type=int, default=8)
    parser.add_argument('--run', action='store_true')
    a = parser.parse_args()
    cfg = json.loads(a.config.read_text())
    if a.output.exists():
        parser.error('output path already exists')
    if not a.run:
        print('Dry run: MTP off/window 4, same-engine accepted-prefix continuation.')
        return 0
    tokenizer_path = Path(cfg['tokenizer'])
    tok = load_tokenizer(tokenizer_path)
    template_path = tokenizer_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    def encode(text):
        return tok.encode(template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
    prompt = encode(exact_prompt(a.prompt_tokens, encode))
    a.output.mkdir(parents=True, exist_ok=False)
    env = child_env(cfg)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                'STRATA_INTEGRATION_TRACE': '1', 'STRATA_MTP_BATCH': '1',
                'STRATA_PREFILL_CPU_SHARE': '0'})
    result = {'prompt_tokens': len(prompt), 'prompt_sha256': hashlib.sha256(json.dumps(prompt).encode()).hexdigest(),
              'initial_tokens': a.initial_tokens, 'continuation_tokens': a.continuation_tokens,
              'state_fields': STATE_KEYS, 'arms': [], 'failures': []}
    for label, window in (('mtp-off', 0), ('mtp-window4', 4)):
        log = a.output / f'{label}.log'
        engine = StrataEngine(str(a.engine.resolve()), args_for(cfg, window), cwd=cfg.get('cwd'),
                              log=str(log), env=env)
        try:
            first = [x for x in engine.generate(prompt, a.initial_tokens, {'temperature': 0}, threading.Event())
                     if x is not None]
            first_hashes = parse_hashes(log)
            require(len(first_hashes) == 1, f'{label}: first request final state missing')
            first_trace = read_accepted_prefix_trace(log)
            require([t for entry in first_trace for t in entry['token_ids']] == first,
                    f'{label}: first trace does not match output')
            continuation_prompt = prompt + first
            continuation = [x for x in engine.generate(continuation_prompt, a.continuation_tokens,
                                                       {'temperature': 0}, threading.Event()) if x is not None]
            final_hashes = parse_hashes(log)
            require(len(final_hashes) == 2, f'{label}: expected two request state fingerprints')
            continuation_trace = read_accepted_prefix_trace(log)
            require([t for entry in continuation_trace for t in entry['token_ids']] == continuation,
                    f'{label}: continuation trace does not match output')
            result['arms'].append({
                'name': label, 'window': window, 'args': args_for(cfg, window),
                'first_ids': first, 'first_state': first_hashes[0], 'first_trace': first_trace,
                'continuation_ids': continuation, 'continuation_state': final_hashes[-1],
                'continuation_trace': continuation_trace,
                'reused_tokens': engine.reused, 'last_request': dict(engine.last),
            })
        finally:
            engine.close()
        (a.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    off, mtp = result['arms']
    for field in ('first_ids', 'continuation_ids'):
        if off[field] != mtp[field]:
            result['failures'].append(f'{field} differ')
    for state_name in ('first_state', 'continuation_state'):
        differences = [key for key in STATE_KEYS if off[state_name].get(key) != mtp[state_name].get(key)]
        result[f'{state_name}_equal'] = not differences
        result[f'{state_name}_differing_fields'] = differences
        if differences:
            result['failures'].append(f'{state_name} differs: {", ".join(differences)}')
    result['passed'] = not result['failures']
    (a.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('passed', 'failures', 'first_state_equal',
              'first_state_differing_fields', 'continuation_state_equal',
              'continuation_state_differing_fields')}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
