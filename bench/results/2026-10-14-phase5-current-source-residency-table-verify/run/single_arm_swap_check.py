#!/usr/bin/env python3
"""Run one short IQ1_M service request with exact refill and residency-table checks."""
import hashlib
import json
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.integration.accepted_prefix_parity import parse_hashes
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

base = ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7'
cfg = json.loads((base / 'baseline-mtp0-config.json').read_text())
argv = list(cfg['args'])
if '--adapt-every' in argv:
    argv[argv.index('--adapt-every') + 1] = '4'
else:
    argv += ['--adapt-every', '4']
if '--adapt-accepted-only' not in argv:
    argv.append('--adapt-accepted-only')
env = child_env(cfg)
env.update({'STRATA_VERIFY_ADAPT_SWAPS': '1', 'STRATA_TRACE_ADAPT': '1',
            'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
            'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
            'STRATA_PREFILL_CPU_SHARE': '0'})
log = Path(__file__).resolve().parent / 'engine.log'
engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
workloads = json.loads((base / 'workloads.json').read_text())['workloads']
long_workload = workloads[0]
tok_path = Path(cfg['tokenizer'])
tok = load_tokenizer(tok_path)
template = ChatTemplate(tok_path / 'chat_template.jinja')
prompt = tok.encode(template.render(long_workload['messages'], enable_thinking=False), parse_special=True)[-512:]
try:
    ids = [int(token) for token in engine.generate(prompt, 16, {'temperature': 0}, threading.Event()) if token is not None]
    hashes = parse_hashes(log)
    result = {'status': 'pass' if len(ids) == 16 and len(hashes) == 1 else 'fail',
              'model': 'Qwen3.8-Flash-Next Coder IQ1_M', 'mtp': 0,
              'prompt_tokens': len(prompt), 'output_tokens': len(ids), 'ids': ids,
              'prompt_sha256': hashlib.sha256(json.dumps(prompt).encode()).hexdigest(),
              'state': hashes[-1] if hashes else None,
              'engine_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest()}
    Path(__file__).resolve().parent.joinpath('result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'output_tokens': len(ids), 'state_fields': len(hashes[-1]) if hashes else 0}))
    if result['status'] != 'pass':
        raise SystemExit(1)
finally:
    engine.close()
