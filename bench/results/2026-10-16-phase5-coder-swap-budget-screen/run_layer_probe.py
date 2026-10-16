#!/usr/bin/env python3
"""Capture every available layer for the first short/long requests."""
import argparse
import gzip
import hashlib
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

BASE = ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7'


def replace_option(argv, name, value):
    if name in argv:
        argv[argv.index(name) + 1] = str(value)
    else:
        argv.extend((name, str(value)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapt-every', type=int, required=True)
    parser.add_argument('--adapt-swaps', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((BASE / 'baseline-mtp0-config.json').read_text())
    argv = list(cfg['args'])
    replace_option(argv, '--adapt-every', args.adapt_every)
    replace_option(argv, '--adapt-swaps', args.adapt_swaps)
    if '--adapt-accepted-only' not in argv:
        argv.append('--adapt-accepted-only')
    if '--expert-cache-cpu-order' in argv:
        raise RuntimeError('CPU-order option is incompatible with the native Coder pack')

    tokenizer_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    workload = json.loads((BASE / 'workloads.json').read_text())['workloads'][0]
    long_ids = tokenizer.encode(template.render(workload['messages'], enable_thinking=False), parse_special=True)
    assert len(long_ids) == 2048, len(long_ids)
    prompts = [('short-512', long_ids[-512:]), ('long-2048', long_ids)]

    capture_raw = args.output / 'all-layers.jsonl'
    capture_gz = args.output / 'all-layers.jsonl.gz'
    log = args.output / 'service.log'
    env = child_env(cfg)
    env.update({
        'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
        'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
        'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_CAPTURE_MOE_LAYER': '-1',
        'STRATA_CAPTURE_MOE_ROWS': '4096', 'STRATA_CAPTURE_MOE_START_ROW': '0',
        'STRATA_CAPTURE_MOE_PATH': str(capture_raw.resolve()),
        'STRATA_VERIFY_ADAPT_SWAPS': '1',
    })
    engine = StrataEngine(cfg['exe'], argv, cwd=cfg['cwd'], log=str(log), env=env)
    requests = []
    try:
        for name, prompt in prompts:
            ids = [int(token) for token in engine.generate(
                prompt, 16, {'temperature': 0}, threading.Event()) if token is not None]
            hashes = parse_hashes(log)
            if len(hashes) != len(requests) + 1:
                raise RuntimeError(f"expected {len(requests) + 1} state records, found {len(hashes)}")
            requests.append({'name': name, 'prompt_tokens': len(prompt), 'ids': ids,
                             'state': hashes[-1]})
            (args.output / 'requests.json').write_text(json.dumps({'requests': requests}, indent=2) + '\n')
    finally:
        engine.close()

    if not capture_raw.is_file():
        raise RuntimeError('missing all-layer capture')
    with capture_raw.open('rb') as source, gzip.open(capture_gz, 'wb', compresslevel=6) as dest:
        while block := source.read(1024 * 1024):
            dest.write(block)
    capture_raw.unlink()
    with gzip.open(capture_gz, 'rt') as source:
        header = json.loads(next(source))
        if header.get('format') != 'strata-moe-dispatch-v2':
            raise RuntimeError(f'unexpected capture header: {header}')
        counts = {}
        rows = 0
        for line in source:
            row = json.loads(line)
            counts[row['layer']] = counts.get(row['layer'], 0) + 1
            rows += 1
    if rows == 0:
        raise RuntimeError('empty all-layer capture')
    analysis = {
        'adapt_every': args.adapt_every, 'adapt_swaps': args.adapt_swaps,
        'captured_rows': rows, 'layer_row_counts': counts,
        'prompt_sha256': {
            'short': hashlib.sha256(json.dumps(list(prompts[0][1])).encode()).hexdigest(),
            'long': hashlib.sha256(json.dumps(long_ids).encode()).hexdigest(),
        },
        'binary_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
    }
    (args.output / 'analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
    print(json.dumps(analysis, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
