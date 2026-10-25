#!/usr/bin/env python3
"""Run one exact-answer retrieval/scoring task under strict NInfer, MTP off/4."""
from __future__ import annotations

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
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--engine', type=Path, required=True)
    ap.add_argument('--workload', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    cfg = json.loads(a.config.read_text())
    workload = json.loads(a.workload.read_text())['workloads'][0]
    expected = (f"EARLY={workload['expected_codes'][0]}, "
                f"MIDDLE={workload['expected_codes'][1]}, "
                f"LATE={workload['expected_codes'][2]}, "
                f"SUM={workload['expected_suffix_sum']}")
    tokenizer_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tokenizer_path)
    template_path = tokenizer_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    prompt_text = workload['messages'][0]['content']
    prompt = tokenizer.encode(template.render(workload['messages'], enable_thinking=False), parse_special=True)
    if len(prompt) != workload['prompt_tokens']:
        raise ValueError(f"fixture says {workload['prompt_tokens']} tokens; formatted prompt has {len(prompt)}")
    if a.output.exists():
        raise ValueError(f'output already exists: {a.output}')
    if not a.run:
        print(json.dumps({'prompt_tokens': len(prompt), 'prompt_sha256': hashlib.sha256(
            json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(), 'expected': expected}, indent=2))
        return 0

    a.output.mkdir(parents=True)
    env = child_env(cfg)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_INTEGRATION_TRACE': '1',
                'STRATA_MTP_BATCH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    result = {'workload': workload['cell'], 'prompt_tokens': len(prompt),
              'prompt_content_sha256': hashlib.sha256(prompt_text.encode()).hexdigest(),
              'prompt_ids_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
              'expected': expected, 'state_fields': STATE_KEYS, 'arms': [], 'failures': []}
    for window in (0, 4):
        name = 'mtp-off' if window == 0 else 'mtp4'
        log = a.output / f'{name}.log'
        command = args_for(cfg, window, disable_adaptive_swaps=True)
        engine = StrataEngine(str(a.engine.resolve()), command, cwd=cfg.get('cwd'),
                              log=str(log), env=env)
        try:
            ids = [token for token in engine.generate(prompt, workload['generate_tokens'],
                    {'temperature': 0}, threading.Event()) if token is not None]
            # The engine intentionally yields its terminal chat token; compare
            # the user-visible answer after removing that protocol marker.
            text = tokenizer.decode(ids).replace('<|im_end|>', '').strip()
            states = parse_hashes(log)
            require(len(states) == 1, f'{name}: expected one final state fingerprint')
            arm = {'name': name, 'window': window, 'args': command, 'ids': ids,
                   'text': text, 'state': states[0], 'usage': dict(engine.last)}
            result['arms'].append(arm)
            if text != expected:
                result['failures'].append(f'{name}: exact answer mismatch: {text!r}')
        except Exception as exc:
            result['failures'].append(f'{name}: {type(exc).__name__}: {exc}')
        finally:
            engine.close()
    if len(result['arms']) == 2:
        off, mtp = result['arms']
        result['token_ids_equal'] = off['ids'] == mtp['ids']
        result['final_state_equal'] = all(off['state'].get(k) == mtp['state'].get(k) for k in STATE_KEYS)
        result['state_differing_fields'] = [k for k in STATE_KEYS if off['state'].get(k) != mtp['state'].get(k)]
        if not result['token_ids_equal']:
            result['failures'].append('MTP-off and MTP4 token IDs differ')
        if not result['final_state_equal']:
            result['failures'].append('MTP-off and MTP4 final state differ')
    result['passed'] = not result['failures'] and len(result['arms']) == 2
    (a.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result.get(k) for k in ('passed', 'failures', 'token_ids_equal',
                   'final_state_equal', 'state_differing_fields')}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
