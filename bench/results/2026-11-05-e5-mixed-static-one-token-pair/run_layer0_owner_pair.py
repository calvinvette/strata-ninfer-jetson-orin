"""Capture routed owner kinds for the first service verifier token."""
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
    pcie_frac = sys.argv[2] if len(sys.argv) > 2 else None
    extra_args = sys.argv[3:]
    output.mkdir(parents=True, exist_ok=False)
    base = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
    command = json.loads(base.read_text())['command']
    index = next(i for i, item in enumerate(command)
                 if item.endswith('/strata') or item == 'build/integration/e0-cuda-build/strata')
    exe = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    if pcie_frac is not None:
        if '--pcie-frac' in args:
            args[args.index('--pcie-frac') + 1] = pcie_frac
        else:
            args.extend(['--pcie-frac', pcie_frac])
    args.extend(extra_args)
    base_env = os.environ.copy()
    base_env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_CAPTURE_MOE_LAYER': '0',
                     'STRATA_CAPTURE_MOE_POSITION': '2', 'STRATA_CAPTURE_MOE_ROWS': '1',
                     'STRATA_CAPTURE_MOE_OUTPUT_LAYER': '0'})
    arms = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        prefix = output / backend
        env = base_env.copy()
        owner = prefix.with_suffix('.owner.jsonl')
        cpu = prefix.with_suffix('.cpu-output.jsonl')
        parts = prefix.with_suffix('.parts.stmparts')
        env['STRATA_CAPTURE_MOE_PATH'] = str(owner)
        env['STRATA_CAPTURE_MOE_OUTPUT_PATH'] = str(cpu)
        env['STRATA_VERIFY_DUMP_MOE_PARTS_LAYER'] = '0'
        env['STRATA_VERIFY_DUMP_MOE_PARTS_POSITION'] = '2'
        env['STRATA_VERIFY_DUMP_MOE_PARTS_PATH'] = str(parts)
        inputs = prefix.with_suffix('.input.stminput')
        env['STRATA_VERIFY_DUMP_MOE_INPUT_LAYER'] = '0'
        env['STRATA_VERIFY_DUMP_MOE_INPUT_POSITION'] = '2'
        env['STRATA_VERIFY_DUMP_MOE_INPUT_PATH'] = str(inputs)
        log = prefix.with_suffix('.log')
        engine = StrataEngine(exe, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            tokens = [int(value) for value in engine.generate([1, 2, 3], 1,
                                                               {'temperature': 0}, threading.Event())
                      if value is not None]
            arms.append({'backend': backend, 'token_ids': tokens,
                         'owner_file': owner.name, 'owner_sha256': hashlib.sha256(owner.read_bytes()).hexdigest(),
                         'cpu_output_file': cpu.name,
                         'cpu_output_sha256': hashlib.sha256(cpu.read_bytes()).hexdigest(),
                         'parts_file': parts.name,
                         'parts_sha256': hashlib.sha256(parts.read_bytes()).hexdigest(),
                         'input_file': inputs.name,
                         'input_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
                         'log_file': log.name})
        finally:
            engine.close()
    result = {'prompt_token_ids': [1, 2, 3], 'captured_layer': 0,
              'captured_position': 2, 'temperature': 0, 'pcie_frac': pcie_frac,
              'extra_args': extra_args,
              'arms': arms,
              'token_ids_equal': arms[0]['token_ids'] == arms[1]['token_ids']}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
