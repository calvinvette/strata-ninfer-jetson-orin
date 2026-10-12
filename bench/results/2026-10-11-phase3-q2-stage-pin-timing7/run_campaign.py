import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
for pair in range(7):
    d = OUT / f'pair-{pair:02d}'
    d.mkdir(exist_ok=True)
    seed = 2026101170 + pair
    command = ['systemd-run', '--user', '--scope', '-p', 'MemoryMax=28G',
               sys.executable, 'tools/integration/run_control.py',
               '--output', str(d / 'supervisor'), '--interval', '0.5', '--timeout', '1200', '--',
               sys.executable, 'tools/integration/stage_buffer_parity.py',
               '--config', str(OUT / 'config.json'), '--engine', 'build/integration/candidate/strata',
               '--output', str(d / 'experiment'), '--prompt-tokens', '512', '--generated-tokens', '64',
               '--pairs', '1', '--seed', str(seed), '--timing-only', '--run']
    with (d / 'launch.log').open('w') as log:
        log.write(json.dumps({'pair': pair, 'seed': seed, 'command': command}) + '\n')
        log.flush()
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        log.write(f'\nreturncode={result.returncode}\n')
    print(f'pair {pair}: returncode={result.returncode}', flush=True)
    if result.returncode:
        print('stopping after failed/aborted supervised pair; raw failure retained', flush=True)
        raise SystemExit(result.returncode)
