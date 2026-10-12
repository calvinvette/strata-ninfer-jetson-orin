#!/usr/bin/env python3
"""Run three fresh Q2_0 graph-owner probes at a 64K context reservation."""
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
script = root / 'run_graph_probe_fine.py'
base = Path('bench/results/2026-10-13-phase3-q2-graph-fine-nvmap/server-config.json')
base_cfg = json.loads(base.read_text())
for index in range(1, 4):
    out = root / f'repeat-{index:02d}'
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(json.dumps(base_cfg))
    cfg['port'] = 18490 + index
    cfg['args'][cfg['args'].index('--max-context') + 1] = '65536'
    cfg['args'][cfg['args'].index('--spec') + 1] = '4'
    cfg['log'] = str((out / 'engine.log').resolve())
    (out / 'server-config.json').write_text(json.dumps(cfg, indent=2) + '\n')
    start = time.monotonic()
    result = subprocess.run([sys.executable, str(script), str(out)], check=False)
    (out / 'probe-exit.json').write_text(json.dumps({
        'repeat': index, 'returncode': result.returncode,
        'elapsed_s': time.monotonic() - start,
        'configured_context': 65536, 'spec': 4}, indent=2) + '\n')
    if result.returncode:
        raise SystemExit(result.returncode)
print('three 64K-context spec4 graph probes passed')
