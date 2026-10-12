#!/usr/bin/env python3
"""Run independent paired scalar versus pinned ggml Q8_0 quantizer repetitions."""
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
exe = Path('build/integration/candidate/q8_0_quant_compare').resolve()
for index, seed in enumerate((20261016, 20261017, 20261018), 1):
    start = time.monotonic()
    result = subprocess.run([str(exe), str(seed)], capture_output=True, text=True)
    out = root / f'rep-{index:02d}.txt'
    out.write_text(result.stdout + result.stderr)
    meta = {'rep': index, 'seed': seed, 'returncode': result.returncode,
            'elapsed_s': time.monotonic() - start}
    (root / f'rep-{index:02d}.json').write_text(json.dumps(meta, indent=2) + '\n')
    if result.returncode:
        print(result.stdout, end='')
        print(result.stderr, file=sys.stderr, end='')
        raise SystemExit(result.returncode)
    print(f'rep-{index}: passed')
