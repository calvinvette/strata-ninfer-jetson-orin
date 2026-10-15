#!/usr/bin/env python3
"""Capture matching layer-0 activations before and after an adaptive long request."""
import argparse
import hashlib
import json
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.integration.accepted_prefix_parity import parse_hashes, STATE_KEYS
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

base = ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7'
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--captures', type=int, default=128)
ap.add_argument('--recovery-start-row', type=int, default=2592)
args = ap.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
cfg = json.loads((base / 'baseline-mtp0-config.json').read_text())
workloads = json.loads((base / 'workloads.json').read_text())['workloads']
long_workload = workloads[0]
tok_path = Path(cfg['tokenizer'])
tok = load_tokenizer(tok_path)
template = ChatTemplate(tok_path / 'chat_template.jinja')
long_ids = tok.encode(template.render(long_workload['messages'], enable_thinking=False), parse_special=True)
assert len(long_ids) == 2048
short_ids = long_ids[-512:]
results = {'sequence': ['short-512', 'long-2048', 'short-512-recovery'],
           'adapt_every': 4, 'tokens_per_request': 16,
           'prompt_sha256': {'short': hashlib.sha256(json.dumps(short_ids).encode()).hexdigest(),
                             'long': hashlib.sha256(json.dumps(long_ids).encode()).hexdigest()},
           'capture_layer': 0, 'capture_rows': args.captures,
           'capture_starts': [0, args.recovery_start_row], 'sessions': []}
for capture_start in results['capture_starts']:
    label = f'start-{capture_start}'
    argv = list(cfg['args'])
    if '--adapt-every' in argv:
        argv[argv.index('--adapt-every') + 1] = '4'
    else:
        argv += ['--adapt-every', '4']
    if '--adapt-accepted-only' not in argv:
        argv.append('--adapt-accepted-only')
    env = child_env(cfg)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
                'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_CAPTURE_MOE_LAYER': '0',
                'STRATA_CAPTURE_MOE_ROWS': str(args.captures),
                'STRATA_CAPTURE_MOE_START_ROW': str(capture_start),
                'STRATA_CAPTURE_MOE_PATH': str((args.output / f'{label}.jsonl').resolve()),
                'STRATA_VERIFY_ADAPT_SWAPS': '1'})
    log = args.output / f'{label}.log'
    engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
    session = {'capture_start': capture_start, 'requests': []}
    try:
        for name, prompt in (('short-512', short_ids), ('long-2048', long_ids),
                             ('short-512-recovery', short_ids)):
            ids = [int(token) for token in engine.generate(prompt, 16, {'temperature': 0}, threading.Event())
                   if token is not None]
            hashes = parse_hashes(log)
            assert len(hashes) == len(session['requests']) + 1, (label, name, len(hashes))
            session['requests'].append({'name': name, 'prompt_tokens': len(prompt), 'ids': ids,
                                       'state': hashes[-1]})
            results['sessions'] = [s for s in results['sessions'] if s['capture_start'] != capture_start]
            results['sessions'].append(session)
            (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    finally:
        engine.close()

reference, recovery = results['sessions']
checks = []
for i, name in enumerate(results['sequence']):
    a, b = reference['requests'][i], recovery['requests'][i]
    checks.append({'request': name, 'outputs_equal_across_replays': a['ids'] == b['ids'],
                   'state_equal_across_replays': all(a['state'][k] == b['state'][k] for k in STATE_KEYS)})
checks.append({'request': 'short-before-vs-after-long',
               'output_equal_within_service': reference['requests'][0]['ids'] == reference['requests'][2]['ids'],
               'state_equal_within_service': reference['requests'][0]['state'] == reference['requests'][2]['state']})
results['checks'] = checks
results['passed'] = all(row.get('outputs_equal_across_replays', True) and
                        row.get('state_equal_across_replays', True) for row in checks[:-1])
for row in checks[-1:]:
    results['same_service_recovery_reproduced'] = not row['output_equal_within_service'] or not row['state_equal_within_service']
(args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({'checks': checks, 'passed': results['passed'],
                  'recovery_reproduced': results.get('same_service_recovery_reproduced')}, indent=2))
