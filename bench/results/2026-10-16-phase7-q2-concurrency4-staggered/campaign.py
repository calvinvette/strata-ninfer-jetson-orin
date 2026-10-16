#!/usr/bin/env python3
"""Repeat staggered four-slot occupancy checks in fresh service processes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPECTED_BINARY = 'fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: campaign.py OUTPUT_DIR')
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((HERE / 'config.json').read_text())
    binary = Path(cfg['exe'])
    binary_hash = digest(binary)
    if binary_hash != EXPECTED_BINARY:
        raise RuntimeError(f'unexpected service binary hash: {binary_hash}')
    campaign = {
        'schema': 1,
        'scope': 'Q2_0 staggered four-request slot-occupancy confirmation; correctness/overlap, no timing comparison',
        'source_binary_sha256': binary_hash,
        'config_sha256': digest(HERE / 'config.json'),
        'workload_sha256': digest(HERE / 'workloads.json'),
        'blocks': [], 'status': 'running',
    }
    campaign_path = out / 'campaign.json'

    def save():
        campaign_path.write_text(json.dumps(campaign, indent=2) + '\n')

    save()
    for block in range(3):
        run_out = out / f'block-{block}'
        launch = out / f'block-{block}.launch.txt'
        started = time.time()
        proc = subprocess.run([sys.executable, str(HERE / 'run.py'), str(run_out)],
                              cwd=ROOT, capture_output=True, text=True)
        launch.write_text(proc.stdout + proc.stderr)
        result_path = run_out / 'result.json'
        result = json.loads(result_path.read_text()) if result_path.is_file() else {}
        passed = proc.returncode == 0 and result.get('status') == 'pass'
        item = {
            'block': block, 'started_wall_time': started, 'finished_wall_time': time.time(),
            'returncode': proc.returncode, 'status': 'pass' if passed else 'fail',
            'max_running': result.get('max_running'),
            'max_active_metric_slots': result.get('max_active_metric_slots'),
            'max_active_http_slots': result.get('max_active_http_slots'),
            'samples': result.get('samples'),
            'quality_pass': result.get('quality_pass'),
            'minimum_reply_prompt_tokens': min((x.get('prompt_tokens', 0) for x in result.get('requests', [])), default=0),
        }
        campaign['blocks'].append(item)
        campaign['status'] = 'running' if passed else 'fail'
        save()
        print(f"block={block} status={item['status']} max_slots="
              f"{item['max_active_metric_slots']}/{item['max_active_http_slots']}", flush=True)
        if not passed:
            campaign['failure'] = f'block {block} failed; see {launch} and {run_out}'
            save()
            return 1
    campaign['status'] = 'pass'
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
