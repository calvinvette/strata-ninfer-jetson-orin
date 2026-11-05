"""Capture first-window logits for a matched service-engine prompt pair."""
from __future__ import annotations
import array
import hashlib
import json
import math
import os
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine


def summarize(values: list[float]) -> dict:
    ids = sorted(range(len(values)), key=values.__getitem__, reverse=True)[:10]
    return {'top10': [{'token_id': i, 'logit': values[i]} for i in ids],
            'top1_margin': values[ids[0]] - values[ids[1]]}


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
    command = json.loads(base.read_text())['command']
    index = next(i for i, item in enumerate(command)
                 if item.endswith('/strata') or item == 'build/integration/e0-cuda-build/strata')
    exe = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    if args[args.index('--max-new') + 1] != '1':
        raise ValueError('expected one-token baseline command')

    env = os.environ.copy()
    env['STRATA_PREFILL_CPU_SHARE'] = '0'
    arms = []
    vectors = {}
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        prefix = output / f'{backend}-first-logits'
        env['STRATA_DUMP_FIRST_LOGITS'] = str(prefix)
        log = output / f'{backend}.log'
        engine = StrataEngine(exe, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            tokens = [int(x) for x in engine.generate([1, 2, 3], 1,
                                                       {'temperature': 0}, threading.Event())
                      if x is not None]
            dump = Path(str(prefix) + '.0')
            raw = dump.read_bytes()
            values = array.array('f')
            values.frombytes(raw)
            if len(values) * values.itemsize != len(raw):
                raise ValueError(f'{dump}: partial float32 vector')
            vectors[backend] = list(values)
            arms.append({'backend': backend, 'token_ids': tokens,
                         'logit_count': len(values), 'logit_sha256': hashlib.sha256(raw).hexdigest(),
                         'logits': summarize(vectors[backend]), 'log_file': log.name,
                         'finish': engine.last})
        finally:
            engine.close()
    s, n = vectors['strata'], vectors['ninfer']
    if len(s) != len(n):
        raise ValueError('service logit vector lengths differ')
    delta = [b - a for a, b in zip(s, n)]
    diff_l2 = math.sqrt(math.fsum(x*x for x in delta))
    s_l2 = math.sqrt(math.fsum(x*x for x in s))
    result = {'prompt_token_ids': [1, 2, 3], 'prefill_cpu_share': 0,
              'arms': arms,
              'comparison': {
                  'token_ids_equal': arms[0]['token_ids'] == arms[1]['token_ids'],
                  'different_logits': sum(a != b for a, b in zip(s, n)),
                  'relative_l2': diff_l2 / max(s_l2, 1e-300),
                  'max_abs': max(map(abs, delta), default=0.0),
                  'rms_abs': math.sqrt(math.fsum(x*x for x in delta) / len(delta)),
                  'top1_equal': arms[0]['logits']['top10'][0]['token_id'] ==
                                arms[1]['logits']['top10'][0]['token_id']}}
    (output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
