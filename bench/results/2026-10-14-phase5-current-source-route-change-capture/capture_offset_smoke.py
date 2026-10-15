#!/usr/bin/env python3
"""Smoke-test layer-filtered activation capture starting at a selected stream row."""
import argparse
import json
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.integration.accepted_prefix_parity import parse_hashes
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
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
capture_path = args.output / 'capture.jsonl'
env.update({'STRATA_CAPTURE_MOE_PATH': str(capture_path.resolve()), 'STRATA_CAPTURE_MOE_LAYER': '0',
            'STRATA_CAPTURE_MOE_ROWS': '2', 'STRATA_CAPTURE_MOE_START_ROW': '4',
            'STRATA_VERIFY_ADAPT_SWAPS': '1', 'STRATA_PREFILL_CPU_SHARE': '0',
            'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1'})
log = args.output / 'engine.log'
engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
workload = json.loads((base / 'workloads.json').read_text())['workloads'][0]
tok_path = Path(cfg['tokenizer'])
tok = load_tokenizer(tok_path)
template = ChatTemplate(tok_path / 'chat_template.jinja')
prompt = tok.encode(template.render(workload['messages'], enable_thinking=False), parse_special=True)[-512:]
try:
    ids = [int(t) for t in engine.generate(prompt, 16, {'temperature': 0}, threading.Event()) if t is not None]
    states = parse_hashes(log)
finally:
    engine.close()
records = [json.loads(line) for line in capture_path.read_text().splitlines()]
rows = records[1:]
result = {'status': 'pass' if len(ids) == 16 and len(states) == 1 and
          [r.get('stream_row') for r in rows] == [4, 5] and all(r['layer'] == 0 for r in rows) else 'fail',
          'captured_stream_rows': [r.get('stream_row') for r in rows], 'captured_layer': 0,
          'prompt_tokens': len(prompt), 'output_tokens': len(ids), 'state': states[-1] if states else None,
          'capture_path': str(capture_path)}
(args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
if result['status'] != 'pass':
    raise SystemExit(1)
