#!/usr/bin/env python3
"""Integrate named tegrastats rails over the current-source Coder MTP × KV requests."""
import csv
import json
import statistics
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

HERE = Path(__file__).resolve().parent
RUNS = HERE / 'campaign'
CONDITIONS = ('fp16-mtp0', 'fp16-mtp4', 'int8-mtp0', 'int8-mtp4')
per_arm = {}

for block in range(7):
    for kv in ('fp16', 'int8'):
        for mtp in (0, 4):
            condition = f'{kv}-mtp{mtp}'
            matches = list(RUNS.glob(
                f'block-{block:02d}-kv-{kv}-workload-*-mtp-{mtp}'))
            if len(matches) != 1:
                raise RuntimeError(f'expected one {block}/{condition} run, got {matches}')
            run = matches[0]
            request = json.loads((run / 'requests.json').read_text())
            measured = [row for row in request['checks'] if not row.get('warmup')]
            if len(measured) != 1 or measured[0]['status'] != 'pass':
                raise RuntimeError(f'invalid measured request: {run}')
            row = measured[0]
            memory = [json.loads(line) for line in
                      (run / 'supervisor/memory.jsonl').read_text().splitlines()]
            if not memory:
                raise RuntimeError(f'missing supervisor clock base: {run}')
            wall_offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']
            rails = rails_from_lines(
                (run / 'supervisor/tegrastats.txt').read_text().splitlines())
            energy = window_energy(
                rails,
                row['request_start_monotonic_s'] + wall_offset,
                row['request_end_monotonic_s'] + wall_offset)
            tokens = row['response']['usage']['completion_tokens']
            per_arm[(block, condition)] = {
                'block': block,
                'condition': condition,
                'kv': kv,
                'mtp_window': mtp,
                'request_seconds': row['request_end_monotonic_s'] - row['request_start_monotonic_s'],
                'output_tokens': tokens,
                'status': energy['status'],
                'reason': energy.get('reason'),
                'joules_by_named_rail': energy.get('joules_by_named_rail', {}),
                'joules_per_output_token_by_named_rail': {
                    rail: value / tokens
                    for rail, value in energy.get('joules_by_named_rail', {}).items()},
            }

if len(per_arm) != 28 or any(row['status'] != 'estimated' for row in per_arm.values()):
    raise RuntimeError('all 28 request windows must have supported rail estimates')
if len({row['output_tokens'] for row in per_arm.values()}) != 1:
    raise RuntimeError('paired arms must emit the same token count')

cell_medians = []
rails = sorted({rail for row in per_arm.values()
                for rail in row['joules_per_output_token_by_named_rail']})
for condition in CONDITIONS:
    for rail in rails:
        values = [row['joules_per_output_token_by_named_rail'][rail]
                  for (block, cond), row in per_arm.items() if cond == condition]
        cell_medians.append({'condition': condition, 'rail': rail,
                             'estimated_blocks': len(values),
                             'median_joules_per_output_token': statistics.median(values)})

comparisons = (
    ('mtp4_vs_mtp0_fp16', 'fp16-mtp4', 'fp16-mtp0'),
    ('mtp4_vs_mtp0_int8', 'int8-mtp4', 'int8-mtp0'),
    ('int8_vs_fp16_mtp0', 'int8-mtp0', 'fp16-mtp0'),
    ('int8_vs_fp16_mtp4', 'int8-mtp4', 'fp16-mtp4'),
)
contrasts = []
for rail in rails:
    effects_by_contrast = {}
    for index, (label, candidate, baseline) in enumerate(comparisons):
        effects = []
        for block in range(7):
            a = per_arm[(block, candidate)]['joules_by_named_rail'][rail]
            b = per_arm[(block, baseline)]['joules_by_named_rail'][rail]
            effects.append(100 * (a / b - 1))
        effects_by_contrast[label] = effects
        contrasts.append({
            'rail': rail,
            'contrast': label,
            'paired_blocks': len(effects),
            'block_effects_percent': effects,
            'median_percent': statistics.median(effects),
            'paired_block_bootstrap_95pct_percent': interval(effects, 20261020 + index),
        })
    interaction = [a - b for a, b in zip(
        effects_by_contrast['mtp4_vs_mtp0_fp16'],
        effects_by_contrast['mtp4_vs_mtp0_int8'])]
    contrasts.append({
        'rail': rail,
        'contrast': 'mtp_by_kv_interaction_fp16_minus_int8_percentage_points',
        'paired_blocks': len(interaction),
        'block_effects_percentage_points': interaction,
        'median_percentage_points': statistics.median(interaction),
        'paired_block_bootstrap_95pct_percentage_points': interval(interaction, 20261025),
    })

result = {
    'scope': ('Separate named tegrastats rails integrated over each API request window; '
              'includes board idle/background and is not process-attributed; rails are not summed.'),
    'method': ('Piecewise-linear integration of instantaneous mW at one-second wall timestamps; '
               'request ends must be bracketed and gaps over 2.5 seconds are unsupported.'),
    'planned_requests': len(per_arm),
    'estimated_windows': sum(row['status'] == 'estimated' for row in per_arm.values()),
    'unsupported_windows': sum(row['status'] != 'estimated' for row in per_arm.values()),
    'per_condition_medians': cell_medians,
    'paired_contrasts': contrasts,
    'per_arm': list(per_arm.values()),
}
(HERE / 'rail-energy.json').write_text(json.dumps(result, indent=2) + '\n')
with (HERE / 'rail-energy-pairs.csv').open('w', newline='') as stream:
    fields = ['block', 'condition', 'request_seconds', 'output_tokens', 'status',
              'reason', 'joules_by_named_rail', 'joules_per_output_token_by_named_rail']
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for row in per_arm.values():
        writer.writerow({field: row[field] for field in fields})
print(json.dumps({'estimated_windows': result['estimated_windows'],
                  'unsupported_windows': result['unsupported_windows'],
                  'per_condition_medians': cell_medians,
                  'paired_contrasts': contrasts}, indent=2))
