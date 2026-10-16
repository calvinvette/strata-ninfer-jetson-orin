#!/usr/bin/env python3
"""Run seven randomized paired Coder adaptive-vs-delayed residency checks."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOCK = Path('/tmp') / f'strata-integration-campaign-{os.getuid()}.lock'
BINARY_SHA256 = 'fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b'
MODEL_SHARDS = {
    'Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf': 'e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad',
    'Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf': '316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113',
}
ARMS = (
    {'name': 'delayed-control', 'adapt_every': 100000, 'adapt_swaps': 96},
    {'name': 'adaptive-cap8', 'adapt_every': 4, 'adapt_swaps': 8},
)


def schedule(seed, blocks):
    rng = random.Random(seed)
    out = []
    for block in range(blocks):
        order = list(ARMS)
        rng.shuffle(order)
        out.extend({'block': block, **arm} for arm in order)
    return out


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=202610167)
    ap.add_argument('--blocks', type=int, default=7)
    ap.add_argument('--continuations', type=int, default=1)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.blocks < 7 or args.continuations < 1:
        ap.error('confirmation needs at least seven blocks and one continuation')
    if args.output.exists():
        ap.error('output path already exists')
    cfg = json.loads((HERE / 'config.json').read_text())
    binary = Path(cfg['exe'])
    actual = sha256(binary)
    if actual != BINARY_SHA256:
        raise RuntimeError(f'unexpected engine binary: {actual}')
    native = Path(cfg['args'][cfg['args'].index('--native') + 1])
    ple = Path(cfg['args'][cfg['args'].index('--ple-gguf') + 1])
    if native.name not in MODEL_SHARDS or ple.name not in MODEL_SHARDS:
        raise RuntimeError('unexpected Coder GGUF shard names')
    rows = schedule(args.seed, args.blocks)
    campaign = {
        'schema': 1,
        'status': 'planned',
        'scope': 'same-service short/long/short/recovery continuation, delayed-adaptation control versus adaptive cap 8; state and token-ID checks; correctness only',
        'seed': args.seed,
        'blocks': args.blocks,
        'continuations': args.continuations,
        'source_commit': 'b2cde9b41b4eab1179a24d80133fc5a236560acb',
        'binary_sha256': actual,
        'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e',
        'model_quantization': 'IQ1_M',
        'model_shard_sha256': MODEL_SHARDS,
        'model_paths': [str(native), str(ple)],
        'runs': rows,
    }
    print(json.dumps({'seed': args.seed, 'blocks': args.blocks, 'schedule': rows}, indent=2))
    if not args.run:
        return 0
    args.output.mkdir(parents=True)
    campaign['status'] = 'running'
    manifest = args.output / 'campaign.json'

    def save():
        tmp = manifest.with_suffix('.tmp')
        tmp.write_text(json.dumps(campaign, indent=2) + '\n')
        tmp.replace(manifest)

    save()
    tools = ROOT / 'tools/integration'
    with LOCK.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise RuntimeError('another supervised Orin campaign owns the device') from e
        for i, row in enumerate(rows):
            d = args.output / f"block-{row['block']:02d}-{row['name']}"
            sup = d / 'supervisor'
            result = d / 'result'
            d.mkdir()
            cmd = [sys.executable, str(tools / 'run_control.py'), '--output', str(sup.resolve()),
                   '--timeout', '1800', '--interval', '1', '--sample-clocks', '--',
                   sys.executable, str(HERE / 'run_one.py'), '--adapt-every', str(row['adapt_every']),
                   '--adapt-swaps', str(row['adapt_swaps']), '--continuations', str(args.continuations),
                   '--output', str(result.resolve())]
            row.update(status='running', command=cmd, directory=str(d.resolve()), started_wall_time=time.time())
            save()
            (d / 'launch.txt').write_text(' '.join(cmd) + '\n')
            completed = subprocess.run(['systemd-run', '--user', '--scope', '--collect', '-p', 'MemoryMax=28G', '-p', 'IOAccounting=yes', *cmd], cwd=ROOT, capture_output=True, text=True)
            with (d / 'launch.txt').open('a') as log:
                log.write(completed.stdout + completed.stderr)
            sup_path = sup / 'result.json'
            api_path = result / 'analysis.json'
            supervisor = json.loads(sup_path.read_text()) if sup_path.exists() else {}
            analysis = json.loads(api_path.read_text()) if api_path.exists() else {}
            passed = completed.returncode == 0 and supervisor.get('status') == 'pass' and analysis.get('binary_sha256') == actual
            row.update(status='pass' if passed else 'fail', returncode=completed.returncode,
                       supervisor_status=supervisor.get('status'),
                       minimum_available_bytes=supervisor.get('minimum_available_bytes'),
                       minimum_admission_available_bytes=supervisor.get('minimum_admission_available_bytes'),
                       elapsed_s=supervisor.get('elapsed_s'), result=analysis,
                       finished_wall_time=time.time())
            save()
            print(f"block={row['block']} arm={row['name']} status={row['status']}", flush=True)
            if not passed:
                for pending in rows[i + 1:]:
                    pending.update(status='not_run', reason='not launched after failed/aborted cell')
                break
        fcntl.flock(lock, fcntl.LOCK_UN)
    campaign['status'] = 'pass' if all(row['status'] == 'pass' for row in rows) else 'fail'
    campaign['finished_wall_time'] = time.time()
    save()
    return 0 if campaign['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
