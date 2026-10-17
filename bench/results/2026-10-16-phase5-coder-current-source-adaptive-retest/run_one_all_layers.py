#!/usr/bin/env python3
"""Capture the first 4-request Coder sequence across all MoE layers."""
import argparse
import gzip
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

BASE = ROOT / 'bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7'

def replace_option(argv, name, value):
    if name in argv:
        argv[argv.index(name) + 1] = str(value)
    else:
        argv.extend((name, str(value)))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adapt-every', type=int, required=True)
    ap.add_argument('--adapt-swaps', type=int, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((BASE / 'config.json').read_text())
    argv = list(cfg['args'])
    replace_option(argv, '--adapt-every', a.adapt_every)
    replace_option(argv, '--adapt-swaps', a.adapt_swaps)
    if '--adapt-accepted-only' not in argv:
        argv.append('--adapt-accepted-only')
    tokenizer_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    workload = json.loads((BASE / 'workloads.json').read_text())['workloads'][0]
    long_ids = tokenizer.encode(template.render(workload['messages'], enable_thinking=False), parse_special=True)
    if len(long_ids) != 2048:
        raise RuntimeError(f'expected 2,048 prompt tokens, got {len(long_ids)}')
    prompts = [('short-512', long_ids[-512:]), ('long-2048', long_ids),
               ('short-512-recovery', long_ids[-512:]), ('short-512-continuation-1', long_ids[-512:])]
    raw = a.output / 'all-layers.jsonl'
    log = a.output / 'service.log'
    env = child_env(cfg)
    env.update({'STRATA_STATE_HASH':'1', 'STRATA_STATE_HASH_GDN':'1',
                'STRATA_ACCEPTED_PREFIX_TRACE':'1', 'STRATA_INTEGRATION_TRACE':'1',
                'STRATA_PREFILL_CPU_SHARE':'0', 'STRATA_CAPTURE_MOE_LAYER':'-1',
                'STRATA_CAPTURE_MOE_ROWS':'4096', 'STRATA_CAPTURE_MOE_START_ROW':'0',
                'STRATA_CAPTURE_MOE_PATH':str(raw.resolve()), 'STRATA_VERIFY_ADAPT_SWAPS':'1'})
    engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
    requests=[]
    try:
        for name, prompt in prompts:
            ids=[int(t) for t in engine.generate(prompt,16,{'temperature':0},threading.Event()) if t is not None]
            hashes=parse_hashes(log)
            if len(hashes)!=len(requests)+1:
                raise RuntimeError(f'{name}: expected {len(requests)+1} state records, got {len(hashes)}')
            requests.append({'name':name,'prompt_tokens':len(prompt),'ids':ids,'state':hashes[-1]})
            (a.output/'requests.json').write_text(json.dumps({'requests':requests},indent=2)+'\n')
    finally:
        engine.close()
    if not raw.exists(): raise RuntimeError('missing all-layer capture')
    counts={}; captured=0
    with raw.open('rt') as src, gzip.open(a.output/'all-layers.jsonl.gz','wt',compresslevel=6) as dst:
        header=json.loads(next(src))
        if header.get('format')!='strata-moe-dispatch-v2': raise RuntimeError(f'unexpected capture header: {header}')
        dst.write(json.dumps(header,separators=(',',':'))+'\n')
        for line in src:
            row=json.loads(line); layer=str(row['layer']); counts[layer]=counts.get(layer,0)+1; captured+=1
            dst.write(line)
    raw.unlink()
    state_changed=[k for k in STATE_KEYS if requests[0]['state'][k]!=requests[2]['state'][k]]
    summary={'adapt_every':a.adapt_every,'adapt_swaps':a.adapt_swaps,
             'binary_sha256':hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
             'prompt_sha256':{'short':hashlib.sha256(json.dumps(list(prompts[0][1])).encode()).hexdigest(),
                              'long':hashlib.sha256(json.dumps(long_ids).encode()).hexdigest()},
             'captured_rows':captured,'layer_row_counts':counts,'requests':requests,
             'recovery_token_differences':sum(x!=y for x,y in zip(requests[0]['ids'],requests[2]['ids'])),
             'recovery_state_changed_fields':state_changed,
             'adaptive_byte_verification_passes':log.read_text().count('adaptive swap byte verification passed'),
             'adaptive_residency_verification_passes':log.read_text().count('adaptive residency table verification passed')}
    (a.output/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('captured_rows','layer_row_counts','recovery_token_differences','recovery_state_changed_fields','adaptive_byte_verification_passes','adaptive_residency_verification_passes')},indent=2))

if __name__=='__main__': raise SystemExit(main())
