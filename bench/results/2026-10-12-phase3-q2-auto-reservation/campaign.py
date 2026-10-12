"""Randomized auto-cache context admission screen, three fresh starts per cell."""
import json
import argparse
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from run_control import run

PYTHON = Path.home() / 'models/strata-orin-validation/pack-venv/bin/python'
RUNNER = ROOT / 'bench/results/2026-10-12-phase3-q2-auto-reservation/reconcile.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'bench/results/2026-10-12-phase3-q2-auto-reservation/randomized-screen')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    order = [8192, 65536] * 3
    random.Random(202610126).shuffle(order)
    manifest = {
        'schema': 1,
        'scope': 'randomized auto-cache context admission; one fixed 512-token prompt and one output token',
        'seed': 202610126,
        'repetitions_per_context': 3,
        'contexts': [8192, 65536],
        'order': order,
        'floor_bytes': 6 * 1024 ** 3,
        'runs': [],
    }
    (out / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for index, context in enumerate(order):
        name = f'run-{index + 1:02d}-context-{context}'
        run_dir = out / name / 'run'
        supervisor = out / name / 'supervisor'
        command = [str(PYTHON), str(RUNNER), '--context', str(context), '--output', str(run_dir)]
        print(f'START {name}', flush=True)
        result = run(command, supervisor, timeout_s=900)
        samples = [json.loads(line) for line in (supervisor / 'memory.jsonl').read_text().splitlines() if line]
        oom_events = max((events.get(key, 0)
                          for sample in samples
                          for cgroup in sample.get('cgroups', [])
                          for events in [cgroup.get('memory_events', {})]
                          for key in ('oom', 'oom_kill', 'oom_group_kill')), default=0)
        record = {'name': name, 'context_tokens': context, 'command': command,
                  'status': result['status'], 'minimum_available_bytes': result.get('minimum_available_bytes'),
                  'elapsed_s': result.get('elapsed_s'), 'reason': result.get('reason'),
                  'maximum_cgroup_oom_event_counter': oom_events}
        workload_path = run_dir / 'workload.json'
        summary_path = run_dir / 'owner-summary.json'
        if workload_path.exists() and summary_path.exists():
            workload = json.loads(workload_path.read_text())
            summary = json.loads(summary_path.read_text())
            record.update(generated_ids=workload['generated_ids'],
                          prompt_sha256=workload['prompt_sha256'],
                          engine_sha256=workload['engine_sha256'],
                          reservations=summary['planned_reservations']['events'],
                          owners={owner['owner']: owner['peak_observed_requested_bytes']
                                  for owner in summary['owners']},
                          observed_peak_by_device=summary['observed_allocation_bytes_by_device']['peak'])
        manifest['runs'].append(record)
        (out / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps(record, sort_keys=True), flush=True)
        if result['status'] != 'pass':
            raise RuntimeError(f'{name} did not pass: {result.get("reason")}')


if __name__ == '__main__':
    main()
