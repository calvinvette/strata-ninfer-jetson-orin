#!/usr/bin/env python3
"""Integrate separate named board rails over the graph/MTP request windows."""
import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

CONDITIONS = ('captured-mtp0', 'eager-mtp0', 'captured-mtp2', 'eager-mtp2')
per_arm = {}
for block in range(7):
    for condition in CONDITIONS:
        run = HERE / 'run-confirmation' / f'block-{block:02d}-{condition}'
        request = json.loads((run / 'requests.json').read_text())
        measured = [row for row in request['checks'] if not row.get('warmup')]
        if len(measured) != 1 or measured[0]['status'] != 'pass':
            raise RuntimeError(f'invalid request: {run}')
        row = measured[0]
        memory = [json.loads(line) for line in (run / 'supervisor/memory.jsonl').read_text().splitlines()]
        offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']
        rails = rails_from_lines((run / 'supervisor/tegrastats.txt').read_text().splitlines())
        energy = window_energy(rails, row['request_start_monotonic_s'] + offset,
                               row['request_end_monotonic_s'] + offset)
        tokens = row['response']['usage']['completion_tokens']
        per_arm[(block, condition)] = {'block': block, 'condition': condition,
            'request_seconds': row['request_end_monotonic_s'] - row['request_start_monotonic_s'],
            'output_tokens': tokens, 'status': energy['status'], 'reason': energy.get('reason'),
            'joules_by_named_rail': energy.get('joules_by_named_rail', {}),
            'joules_per_output_token_by_named_rail': {
                rail: value / tokens for rail, value in energy.get('joules_by_named_rail', {}).items()}}

comparisons = [
    ('captured_vs_eager_mtp0', 'captured-mtp0', 'eager-mtp0'),
    ('captured_vs_eager_mtp2', 'captured-mtp2', 'eager-mtp2'),
    ('mtp2_vs_mtp0_captured', 'captured-mtp2', 'captured-mtp0'),
    ('mtp2_vs_mtp0_eager', 'eager-mtp2', 'eager-mtp0')]
contrasts = []
for rail in sorted({name for row in per_arm.values() for name in row['joules_by_named_rail']}):
    for label, candidate, baseline in comparisons:
        effects = []
        for block in range(7):
            a, b = per_arm[(block, candidate)], per_arm[(block, baseline)]
            if a['status'] == b['status'] == 'estimated' and rail in a['joules_by_named_rail'] and rail in b['joules_by_named_rail']:
                effects.append(100 * (a['joules_by_named_rail'][rail] / b['joules_by_named_rail'][rail] - 1))
        contrasts.append({'rail': rail, 'contrast': label, 'paired_blocks': len(effects),
            'block_effects_percent': effects,
            'median_percent': statistics.median(effects) if effects else None,
            'paired_block_bootstrap_95pct_percent': interval(effects, 20261017) if len(effects) >= 2 else None})
    interaction = []
    for block in range(7):
        a,b,c,d = (per_arm[(block,'captured-mtp2')], per_arm[(block,'eager-mtp2')],
                   per_arm[(block,'captured-mtp0')], per_arm[(block,'eager-mtp0')])
        if all(x['status']=='estimated' and rail in x['joules_by_named_rail'] for x in (a,b,c,d)):
            interaction.append(100*(a['joules_by_named_rail'][rail]/b['joules_by_named_rail'][rail]-1)
                               -100*(c['joules_by_named_rail'][rail]/d['joules_by_named_rail'][rail]-1))
    contrasts.append({'rail': rail, 'contrast': 'capture_by_mtp_interaction_percentage_points',
        'paired_blocks': len(interaction), 'block_effects_percentage_points': interaction,
        'median_percentage_points': statistics.median(interaction) if interaction else None,
        'paired_block_bootstrap_95pct_percentage_points': interval(interaction, 20261018) if len(interaction)>=2 else None})

cell_medians=[]
for condition in CONDITIONS:
    for rail in sorted({name for row in per_arm.values() for name in row['joules_per_output_token_by_named_rail']}):
        values=[row['joules_per_output_token_by_named_rail'][rail] for (block,cond),row in per_arm.items()
                if cond==condition and row['status']=='estimated' and rail in row['joules_per_output_token_by_named_rail']]
        cell_medians.append({'condition':condition,'rail':rail,'estimated_blocks':len(values),
            'median_joules_per_output_token':statistics.median(values) if values else None})

result={'scope':'Separate named tegrastats rails integrated over each API request window; includes board idle/background, is not process-attributed, and rails are not summed.',
 'method':'Piecewise-linear integration of instantaneous mW at one-second wall timestamps; request ends must be bracketed and gaps over 2.5 seconds are unsupported.',
 'planned_requests':len(per_arm),'estimated_windows':sum(x['status']=='estimated' for x in per_arm.values()),
 'unsupported_windows':sum(x['status']!='estimated' for x in per_arm.values()),'per_condition_medians':cell_medians,
 'paired_contrasts':contrasts,'per_arm':list(per_arm.values())}
(HERE/'rail-energy.json').write_text(json.dumps(result,indent=2)+'\n')
with (HERE/'rail-energy-pairs.csv').open('w',newline='') as stream:
    fields=['block','condition','request_seconds','output_tokens','status','reason','joules_by_named_rail','joules_per_output_token_by_named_rail']
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for row in per_arm.values():writer.writerow(row)
print(json.dumps({'estimated_windows':result['estimated_windows'],'unsupported_windows':result['unsupported_windows'],
                  'per_condition_medians':cell_medians,'paired_contrasts':contrasts},indent=2))
