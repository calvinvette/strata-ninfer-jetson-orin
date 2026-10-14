#!/usr/bin/env python3
"""Check exact retrieval quality across same-service adaptive cache residency changes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.integration.accepted_prefix_parity import args_for, STATE_KEYS
from tools.conversation_cache_parity import load_tokenizer
from tools.integration.pool_worker_screen import read_accepted_prefix_trace
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

SEQUENCE = ('short-8192', 'long-16384', 'short-8192-recovery')


def encode_workload(workload, tokenizer, template):
    rendered = template.render(workload['messages'],
                               enable_thinking=workload.get('chat_template_kwargs', {}).get('enable_thinking', False))
    ids = tokenizer.encode(rendered, parse_special=True)
    if len(ids) != workload['prompt_tokens']:
        raise ValueError(f"{workload['cell']}: expected {workload['prompt_tokens']} tokens, encoded {len(ids)}")
    return [int(token) for token in ids]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--short-workload', type=Path, required=True)
    parser.add_argument('--long-workload', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--generation-cap', type=int, default=48)
    parser.add_argument('--adapt-every', type=int,
                        help='override the configured adaptive-swap interval (accepted-token rounds)')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    tok_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tok_path)
    template_path = tok_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    short_workload = json.loads(args.short_workload.read_text())['workloads'][0]
    long_workload = json.loads(args.long_workload.read_text())['workloads'][0]
    short_ids = encode_workload(short_workload, tokenizer, template)
    long_ids = encode_workload(long_workload, tokenizer, template)
    if short_workload['expected_codes'] != long_workload['expected_codes']:
        raise ValueError('short and long workload marker oracle differs')
    expected_codes = short_workload['expected_codes']
    expected_text = f"EARLY={expected_codes[0]}, MIDDLE={expected_codes[1]}, LATE={expected_codes[2]}"
    inputs = {'short-8192': short_ids, 'long-16384': long_ids,
              'short-8192-recovery': short_ids}
    results = {
        'sequence': list(SEQUENCE),
        'expected_codes': expected_codes,
        'expected_answer_text': expected_text,
        'generation_cap': args.generation_cap,
        'prompt_tokens': {name: len(ids) for name, ids in inputs.items()},
        'prompt_token_sha256': {name: hashlib.sha256(json.dumps(ids).encode()).hexdigest()
                                for name, ids in inputs.items()},
        'arms': [],
    }
    base_args = list(cfg['args'])
    for window in (0, 4):
        label = 'mtp-off' if window == 0 else 'mtp4'
        engine_args = args_for(cfg, window, disable_adaptive_swaps=False)
        if args.adapt_every is not None:
            if '--adapt-every' in engine_args:
                engine_args[engine_args.index('--adapt-every') + 1] = str(args.adapt_every)
            else:
                engine_args += ['--adapt-every', str(args.adapt_every)]
        # The repeated 8K prompt must be a fresh prefill; only expert residency persists.
        engine_args[engine_args.index('--prompt-cache') + 1] = '0'
        env = child_env(cfg)
        env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                    'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
                    'STRATA_TRACE_ADAPT': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
        env.pop('STRATA_MTP_BATCH', None)
        log_path = args.output / f'{label}.log'
        engine = StrataEngine(cfg['exe'], engine_args, cwd=cfg['cwd'], log=str(log_path), env=env)
        arm = {'name': label, 'window': window, 'engine_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
               'adapt_every': args.adapt_every, 'args': engine_args, 'requests': []}
        try:
            prior_trace_rows = 0
            for name in SEQUENCE:
                ids = inputs[name]
                generated = [int(token) for token in engine.generate(
                    ids, args.generation_cap, {'temperature': 0}, threading.Event()) if token is not None]
                decoded = tokenizer.decode(generated).strip()
                # The engine includes its terminal protocol stop token in emitted IDs.
                decoded = decoded.removesuffix('<|im_end|>').rstrip()
                all_trace = read_accepted_prefix_trace(log_path)
                trace = all_trace[prior_trace_rows:]
                prior_trace_rows = len(all_trace)
                if not trace:
                    raise ValueError(f'{label}/{name}: no accepted-prefix state trace for request')
                traced_ids = [token for row in trace for token in row['token_ids']]
                if traced_ids != generated:
                    raise ValueError(f'{label}/{name}: accepted-prefix trace differs from published token IDs')
                code_counts = {code: decoded.count(code) for code in expected_codes}
                passed = decoded == expected_text and all(code_counts[code] == 1 for code in expected_codes)
                arm['requests'].append({
                    'name': name, 'prompt_tokens': len(ids), 'token_ids': generated,
                    'answer': decoded, 'answer_sha256': hashlib.sha256(decoded.encode()).hexdigest(),
                    'completion_tokens': len(generated), 'finish': engine.last.get('finish'),
                    'usage': engine.last, 'expected_code_counts': code_counts,
                    'quality_pass': passed, 'state': trace[-1]['state'],
                    'accepted_prefix_trace': trace,
                })
                results['arms'] = [item for item in results['arms'] if item['name'] != label] + [arm]
                (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        finally:
            engine.close()
    by_name = {arm['name']: arm for arm in results['arms']}
    checks = []
    for index, name in enumerate(SEQUENCE):
        off = by_name['mtp-off']['requests'][index]
        mtp = by_name['mtp4']['requests'][index]
        checks.append({'request': name,
                       'quality_pass_both': off['quality_pass'] and mtp['quality_pass'],
                       'answer_equal_across_mtp': off['answer'] == mtp['answer'],
                       'state_equal_across_mtp': all(off['state'][key] == mtp['state'][key] for key in STATE_KEYS)})
    for label in ('mtp-off', 'mtp4'):
        first, recovery = by_name[label]['requests'][0], by_name[label]['requests'][2]
        checks.append({'request': f'{label}-recovery',
                       'quality_pass_both': first['quality_pass'] and recovery['quality_pass'],
                       'same_answer_before_after_long': first['answer'] == recovery['answer'],
                       'same_state_before_after_long': all(first['state'][key] == recovery['state'][key]
                                                           for key in STATE_KEYS)})
    results['checks'] = checks
    results['passed'] = all(row.get('quality_pass_both', True) and
                            row.get('answer_equal_across_mtp', True) and
                            row.get('state_equal_across_mtp', True) and
                            row.get('same_answer_before_after_long', True) and
                            row.get('same_state_before_after_long', True) for row in checks)
    (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'checks': checks, 'passed': results['passed']}, indent=2))
    return 0 if results['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
