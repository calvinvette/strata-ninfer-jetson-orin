#!/usr/bin/env python3
"""Exercise accepted-only state through elastic KV grow/trim on captured graphs."""
import argparse
import hashlib
import json
import re
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.integration.accepted_prefix_parity import parse_hashes, STATE_KEYS
from tools.integration.pool_worker_screen import read_accepted_prefix_trace
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env


def encode(tok, template, content):
    return tok.encode(template.render([{'role': 'user', 'content': content}], enable_thinking=False),
                      parse_special=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-dir', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--context', type=int, default=16384)
    parser.add_argument('--long-tokens', type=int, default=9000)
    parser.add_argument('--tokens', type=int, default=8)
    parser.add_argument('--adapt-every', type=int, default=100000)
    parser.add_argument('--no-kv-grow', action='store_true',
                        help='retain the same context and prompts but use eager full-context KV backing')
    args = parser.parse_args()
    if args.long_tokens + args.tokens >= args.context:
        parser.error('long prompt plus generated tokens must fit the configured context')
    args.output.mkdir(parents=True, exist_ok=False)
    workload = json.loads(args.workloads.read_text())['workloads'][0]
    configs = [json.loads((args.config_dir / f'baseline-mtp{mtp}-config.json').read_text())
               for mtp in (0, 4)]
    tok_path = Path(configs[0]['tokenizer'])
    tok = load_tokenizer(tok_path)
    template = ChatTemplate(tok_path / 'chat_template.jinja')
    source_text = workload['messages'][0]['content']
    prefix = source_text + '\n\nAdditional log markers: '
    low, high = 0, args.long_tokens * 2
    long_text = None
    long_ids = None
    while low <= high:
        repetitions = (low + high) // 2
        candidate = prefix + 'x ' * repetitions
        candidate_ids = encode(tok, template, candidate)
        if len(candidate_ids) == args.long_tokens:
            long_text, long_ids = candidate, candidate_ids
            break
        if len(candidate_ids) < args.long_tokens:
            low = repetitions + 1
        else:
            high = repetitions - 1
    if long_ids is None:
        parser.error('could not construct the requested exact long prompt length')
    short_ids = long_ids[-512:]
    results = {'sequence': ['short-512', f'long-{args.long_tokens}', 'short-512-recovery'],
               'context': args.context, 'adapt_every': args.adapt_every,
               'kv_grow': not args.no_kv_grow,
               'kv_grow_init_cells': 2048, 'kv_grow_step_cells': 2048,
               'tokens_per_request': args.tokens,
               'prompt_token_sha256': {'short': hashlib.sha256(json.dumps(short_ids).encode()).hexdigest(),
                                       'long': hashlib.sha256(json.dumps(long_ids).encode()).hexdigest()},
               'arms': []}
    for cfg, mtp in zip(configs, (0, 4)):
        label = f'mtp{mtp}'
        argv = list(cfg['args'])
        argv[argv.index('--max-context') + 1] = str(args.context)
        argv[argv.index('--adapt-every') + 1] = str(args.adapt_every)
        if not args.no_kv_grow and '--kv-grow' not in argv:
            argv.append('--kv-grow')
        if args.no_kv_grow and '--no-kv-grow' not in argv:
            argv.append('--no-kv-grow')
        if '--suffix-draft' in argv:
            argv[argv.index('--suffix-draft') + 1] = '0'
        env = child_env(cfg)
        env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                    'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
                    'STRATA_PREFILL_CPU_SHARE': '0'})
        if not args.no_kv_grow:
            env.update({'STRATA_KV_GROW_INIT': '2048', 'STRATA_KV_GROW_STEP': '2048'})
        env.pop('STRATA_MTP_BATCH', None)
        log = args.output / f'{label}.log'
        engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
        arm = {'name': label, 'engine_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
               'requests': []}
        try:
            for name, prompt in (('short-512', short_ids), (f'long-{args.long_tokens}', long_ids),
                                 ('short-512-recovery', short_ids)):
                ids = [int(token) for token in engine.generate(
                    prompt, args.tokens, {'temperature': 0}, threading.Event()) if token is not None]
                hashes = parse_hashes(log)
                trace = read_accepted_prefix_trace(log)
                trace_ids = [token for row in trace for token in row['token_ids']]
                assert len(hashes) == len(arm['requests']) + 1
                assert trace_ids == ids, (label, name, 'trace tokens differ from published IDs')
                arm['requests'].append({'name': name, 'prompt_tokens': len(prompt), 'ids': ids,
                                        'text': tok.decode(ids), 'state': hashes[-1], 'trace': trace,
                                        'usage': engine.last})
                results['arms'] = ([arm] if not results['arms'] else results['arms'])
                if results['arms'][-1]['name'] == label:
                    results['arms'][-1] = arm
                else:
                    results['arms'].append(arm)
                (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        finally:
            engine.close()
        lines = log.read_text(errors='replace').splitlines()
        captures = [i for i, line in enumerate(lines) if 'strata verify: captured the ' in line]
        grows = [i for i, line in enumerate(lines) if re.search(r'strata: K/V grown to ', line)]
        trims = [i for i, line in enumerate(lines) if re.search(r'strata: K/V trimmed to ', line)]
        assert captures
        if not args.no_kv_grow:
            assert grows and trims, (label, len(grows), len(trims))
            assert max(captures) < min(grows), (label, captures, grows)
        else:
            assert not grows and not trims, (label, grows, trims)
        arm['captured_graph_events'] = [lines[i] for i in captures]
        arm['kv_growth_events'] = [lines[i] for i in grows]
        arm['kv_trim_events'] = [lines[i] for i in trims]
        arm['captured_graphs_before_growth'] = len(captures)

    reference, candidate = results['arms']
    checks = []
    for index, name in enumerate(results['sequence']):
        a, b = reference['requests'][index], candidate['requests'][index]
        checks.append({'request': name, 'mtp_output_equal': a['ids'] == b['ids'],
                       'mtp_state_equal': all(a['state'][key] == b['state'][key] for key in STATE_KEYS)})
    checks.append({'request': 'short-before-vs-after-grow-trim',
                   'mtp0_output_equal': reference['requests'][0]['ids'] == reference['requests'][2]['ids'],
                   'mtp4_output_equal': candidate['requests'][0]['ids'] == candidate['requests'][2]['ids'],
                   'mtp0_state_equal': reference['requests'][0]['state'] == reference['requests'][2]['state'],
                   'mtp4_state_equal': candidate['requests'][0]['state'] == candidate['requests'][2]['state']})
    results['checks'] = checks
    results['passed'] = all(row.get('mtp_output_equal', True) and row.get('mtp_state_equal', True)
                            and row.get('mtp0_output_equal', True) and row.get('mtp4_output_equal', True)
                            and row.get('mtp0_state_equal', True) and row.get('mtp4_state_equal', True)
                            for row in checks)
    (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'checks': checks, 'passed': results['passed']}, indent=2))
    return 0 if results['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
