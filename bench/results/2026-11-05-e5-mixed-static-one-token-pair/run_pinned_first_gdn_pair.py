"""Capture the committed one-token GDN state under static pinned-PCIe routing."""
from __future__ import annotations
import hashlib
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
    command = json.loads(base.read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    args[args.index('--max-new') + 1] = '1'
    args.extend(['--pcie-frac', '1.0', '--resident-budget-gib', '1',
                 '--adapt-every', '0', '--adapt-swaps', '0'])
    env = os.environ.copy()
    env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_RESIDENT_HEADROOM_GIB': '6',
                'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_STATE_DUMP_GDN_AT': '3'})
    arms = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        prefix = output / backend
        dump = prefix.with_suffix('.gdn.bin')
        arm_env = env.copy()
        arm_env['STRATA_STATE_DUMP_GDN'] = str(dump)
        log = prefix.with_suffix('.txt')
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=arm_env)
        try:
            tokens = [int(value) for value in engine.generate([1, 2, 3], 1,
                                                               {'temperature': 0}, threading.Event())
                      if value is not None]
            arms.append({'backend': backend, 'tokens': tokens, 'finish': engine.last,
                         'dump_file': dump.name,
                         'dump_sha256': hashlib.sha256(dump.read_bytes()).hexdigest(),
                         'log_file': log.name,
                         'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        finally:
            engine.close()
    result = {'prompt_token_ids': [1, 2, 3], 'max_new': 1,
              'dump_state_length': 3, 'resident_budget_gib': 1, 'pcie_frac': 1.0,
              'adaptation': 'disabled', 'arms': arms,
              'token_ids_equal': arms[0]['tokens'] == arms[1]['tokens']}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'tokens': {a['backend']: a['tokens'] for a in arms},
                      'token_ids_equal': result['token_ids_equal']}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
