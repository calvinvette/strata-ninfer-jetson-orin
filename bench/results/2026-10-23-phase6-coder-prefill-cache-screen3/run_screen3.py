#!/usr/bin/env python3
"""Run three randomized Coder prefill-chunk x expert-cache screening blocks."""
import json
import argparse
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'tools' / 'integration'))

from tools.integration.cache_context_screen import api_command, replace_option
from tools.integration.run_control import write_result

CONFIG = json.loads((ROOT / 'config.json').read_text())
WORKLOADS = ROOT / 'workloads.json'
TOOLS = Path('tools/integration').resolve()
CACHES = [1500, 3000]
CHUNKS = [32, 128]


def run_block(block):
    seed = 2026102310 + block
    cells = []
    for cache in CACHES:
        for chunk in CHUNKS:
            cfg = dict(CONFIG)
            args = replace_option(CONFIG['args'], '--expert-cache', cache)
            cfg['args'] = replace_option(args, '--prefill', chunk)
            cells.append({'name': f'cache{cache}-prefill{chunk}',
                          'expert_cache_slots': cache, 'prefill_chunk': chunk,
                          'config': cfg})
    random.Random(seed).shuffle(cells)
    outroot = ROOT / 'per-cell-scopes' / f'block-{block:02d}'
    outroot.mkdir(parents=True, exist_ok=False)
    campaign = {'seed': seed, 'cache_slots': CACHES, 'prefill_chunks': CHUNKS,
                'planned_cells': len(cells), 'rounds_per_cell': 1,
                'warmups_per_cell': 1,
                'scope': 'randomized order; fresh service per cell; one measured request plus one warmup; descriptive screening only',
                'started_wall_time_s': time.time(), 'cells': []}
    manifest = outroot / 'campaign.json'
    write_result(manifest, campaign)
    for index, cell in enumerate(cells):
        name = cell['name']
        out = outroot / name
        out.mkdir()
        cfgpath = out / 'config.json'
        cfgpath.write_text(json.dumps(cell.pop('config'), indent=2) + '\n')
        req = out / 'requests.json'
        command = api_command(Path(sys.executable), TOOLS, cfgpath, WORKLOADS,
                              req, 1, timeout_s=1800, no_trace=True,
                              sample_clocks=True, scope_memory_gib=28)
        row = dict(cell, order=index, status='not_run', command=command)
        campaign['cells'].append(row)
        write_result(manifest, campaign)
        print(f'block {block}: starting {name}', flush=True)
        with (out / 'supervisor.txt').open('w') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        terminal = out / 'supervisor' / 'result.json'
        if terminal.exists():
            result = json.loads(terminal.read_text())
            row.update(status=result['status'],
                       minimum_available_bytes=result.get('minimum_available_bytes'),
                       minimum_admission_available_bytes=result.get('minimum_admission_available_bytes'),
                       elapsed_s=result.get('elapsed_s'), reason=result.get('reason'),
                       supervisor_returncode=code)
        else:
            row.update(status='fail', reason='missing supervisor terminal record',
                       supervisor_returncode=code)
        if req.exists():
            measured = json.loads(req.read_text())
            row['request_summary'] = measured.get('summary')
            row['measured_samples'] = sum(s.get('passed_samples', 0)
                                          for s in measured.get('summary', []))
        write_result(manifest, campaign)
        print(f'block {block}: finished {name} {row["status"]}', flush=True)
        if row['status'] != 'pass':
            for pending in campaign['cells'][index + 1:]:
                pending['status'] = 'not_run'
                pending['reason'] = 'not launched after failed/pressure-aborted cell'
            write_result(manifest, campaign)
            return False
    campaign['finished_wall_time_s'] = time.time()
    write_result(manifest, campaign)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--block', type=int, choices=(1, 2, 3),
                        help='run one block; omit to run every block sequentially')
    opts = parser.parse_args()
    blocks = [opts.block] if opts.block else range(1, 4)
    for block in blocks:
        if not run_block(block):
            raise SystemExit(1)
