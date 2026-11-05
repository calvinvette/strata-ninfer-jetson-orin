#!/usr/bin/env python3
"""Run the guarded Coder 512-token/91-token-output screen across context caps."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
OUT = ROOT / 'bench/results/2026-11-05-e6-coder-capacity-screen'
CAPACITIES = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]
ORDERS = 'strata,ninfer;ninfer,strata;strata,ninfer;ninfer,strata'


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'campaign.json').exists():
        raise FileExistsError(f'campaign already exists: {OUT / "campaign.json"}')
    runner = ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py'
    control = ROOT / 'tools/integration/run_control.py'
    results = []
    campaign_path = OUT / 'campaign.json'
    for capacity in CAPACITIES:
        cell = OUT / f'context-{capacity}'
        supervisor = OUT / f'supervisor-{capacity}'
        command = [sys.executable, str(control), '--output', str(supervisor),
                   '--sample-clocks', '--timeout', '3600', '--',
                   sys.executable, str(runner), str(cell),
                   f'--orders={ORDERS}', '--input-tokens=512',
                   f'--context-tokens={capacity}', '--staged-pcie-gib=6', '--static-owner']
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        (OUT / f'controller-{capacity}.stdout.txt').write_text(proc.stdout)
        (OUT / f'controller-{capacity}.stderr.txt').write_text(proc.stderr)
        result_path = cell / 'results.json'
        result = json.loads(result_path.read_text()) if result_path.exists() else None
        results.append({'capacity': capacity, 'returncode': proc.returncode,
                        'status': result['status'] if result else 'no_result',
                        'results_path': str(result_path.relative_to(ROOT)) if result else None,
                        'supervisor_result': str((supervisor / 'result.json').relative_to(ROOT))
                        if (supervisor / 'result.json').exists() else None})
        campaign = {'date': time.strftime('%Y-%m-%d'),
                    'hardware': 'Jetson AGX Orin, SM87, CUDA 12.6',
                    'model': 'Coder IQ1_M Qwen3.8-Flash-Next',
                    'input_tokens': 512, 'context_capacities': CAPACITIES,
                    'pairs_per_capacity': 4, 'orders': ORDERS,
                    'profile': 'static 6 GiB PCIe complement, adapt-every=0',
                    'prefill_cpu_share': 0, 'guard_gib': 6,
                    'cells': results, 'completed': len(results),
                    'status': 'in_progress' if len(results) < len(CAPACITIES) else 'complete'}
        campaign_path.write_text(json.dumps(campaign, indent=2) + '\n')
        if proc.returncode != 0 or result is None or result.get('status') != 'complete_quality_pass':
            campaign['status'] = 'stopped_on_failed_cell'
            campaign_path.write_text(json.dumps(campaign, indent=2) + '\n')
            return proc.returncode or 2
    print(campaign_path.read_text())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
