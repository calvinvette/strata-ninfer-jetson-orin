#!/usr/bin/env python3
"""Check accepted-only state/output recovery across a long request on one service."""
import argparse
import hashlib
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-dir', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tokens', type=int, default=16)
    parser.add_argument('--adapt-every', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    workloads = json.loads(args.workloads.read_text())['workloads']
    long_workload = workloads[0]
    config_dir = args.config_dir.resolve()
    configs = [json.loads((config_dir / f'baseline-mtp{mtp}-config.json').read_text())
               for mtp in (0, 4)]
    tok_path = Path(configs[0]['tokenizer'])
    tok = load_tokenizer(tok_path)
    template = ChatTemplate(tok_path / 'chat_template.jinja')
    long_ids = tok.encode(template.render(long_workload['messages'], enable_thinking=False),
                          parse_special=True)
    assert len(long_ids) == long_workload['prompt_tokens'] == 2048
    short_ids = long_ids[-512:]
    results = {'sequence': ['short-512', 'long-2048', 'short-512-recovery'],
               'adapt_every': args.adapt_every,
               'tokens_per_request': args.tokens,
               'prompt_token_sha256': {'short': hashlib.sha256(json.dumps(short_ids).encode()).hexdigest(),
                                       'long': hashlib.sha256(json.dumps(long_ids).encode()).hexdigest()},
               'arms': []}
    for cfg, mtp in zip(configs, (0, 4)):
        label = f'mtp{mtp}'
        argv = list(cfg['args'])
        if '--adapt-every' in argv:
            argv[argv.index('--adapt-every') + 1] = str(args.adapt_every)
        else:
            argv += ['--adapt-every', str(args.adapt_every)]
        if '--adapt-accepted-only' not in argv:
            argv.append('--adapt-accepted-only')
        env = child_env(cfg)
        env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                    'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
                    'STRATA_PREFILL_CPU_SHARE': '0'})
        env.pop('STRATA_MTP_BATCH', None)
        log = args.output / f'{label}.log'
        engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
        arm = {'name': label, 'engine_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
               'requests': []}
        try:
            for name, prompt in (('short-512', short_ids), ('long-2048', long_ids),
                                 ('short-512-recovery', short_ids)):
                ids = [int(token) for token in engine.generate(
                    prompt, args.tokens, {'temperature': 0}, threading.Event()) if token is not None]
                hashes = parse_hashes(log)
                trace = read_accepted_prefix_trace(log)
                traced_ids = [token for row in trace for token in row['token_ids']]
                assert len(hashes) == len(arm['requests']) + 1, (label, name, len(hashes))
                assert traced_ids == ids, (label, name, 'accepted-prefix trace differs from published IDs')
                arm['requests'].append({'name': name, 'prompt_tokens': len(prompt), 'ids': ids,
                                        'text': tok.decode(ids), 'finish': engine.last.get('finish'),
                                        'state': hashes[-1], 'trace': trace,
                                        'usage': engine.last})
                results['arms'] = [*results.get('arms', []), arm] if not results.get('arms') else results['arms']
                if results['arms'] and results['arms'][-1]['name'] == label:
                    results['arms'][-1] = arm
                else:
                    results['arms'].append(arm)
                (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        finally:
            engine.close()

    reference, candidate = results['arms']
    checks = []
    for index, name in enumerate(results['sequence']):
        a, b = reference['requests'][index], candidate['requests'][index]
        checks.append({'request': name, 'mtp_output_equal': a['ids'] == b['ids'],
                       'mtp_state_equal': all(a['state'][key] == b['state'][key] for key in STATE_KEYS)})
    checks.append({'request': 'short-before-vs-after-long',
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
