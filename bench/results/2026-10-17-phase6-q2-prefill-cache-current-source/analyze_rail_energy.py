#!/usr/bin/env python3
"""Integrate per-request named rails and paired cache/prefill contrasts."""
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

arms = []
for block in range(1, 8):
    campaign = json.loads((HERE / f'block-{block:02d}/campaign.json').read_text())
    for cell in campaign['cells']:
        cache, prefill = cell['expert_cache_argument'], cell['prefill_chunk_tokens']
        run = HERE / f"block-{block:02d}/{cell['name']}"
        request = json.loads((run / 'requests.json').read_text())
        measured = [row for row in request['checks'] if not row.get('warmup')]
        if len(measured) != 1 or measured[0]['status'] != 'pass':
            raise RuntimeError(f'invalid measured request: block {block} {cell["name"]}')
        row = measured[0]
        memory = [json.loads(line) for line in (run / 'supervisor/memory.jsonl').read_text().splitlines()]
        offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']
        samples = rails_from_lines((run / 'supervisor/tegrastats.txt').read_text().splitlines())
        estimate = window_energy(samples,
            row['request_start_monotonic_s'] + offset,
            row['request_end_monotonic_s'] + offset)
        tokens = row['response']['usage']['completion_tokens']
        arms.append({'block': block, 'cache_slots': cache, 'prefill_chunk': prefill,
            'request_seconds': row['request_end_monotonic_s'] - row['request_start_monotonic_s'],
            'output_tokens': tokens, 'status': estimate['status'], 'reason': estimate.get('reason'),
            'joules_by_named_rail': estimate.get('joules_by_named_rail', {}),
            'joules_per_output_token_by_named_rail': {
                rail: value / tokens for rail, value in estimate.get('joules_by_named_rail', {}).items()}})

by_cell = {(row['block'], row['cache_slots'], row['prefill_chunk']): row for row in arms}
contrasts = []
for rail in sorted({rail for row in arms for rail in row['joules_by_named_rail']}):
    for kind, conditions in [
        ('prefill128_vs32_at_cache3000', [(3000, 128, 3000, 32)]),
        ('prefill128_vs32_at_cache3500', [(3500, 128, 3500, 32)]),
        ('cache3500_vs3000_at_prefill32', [(3500, 32, 3000, 32)]),
        ('cache3500_vs3000_at_prefill128', [(3500, 128, 3000, 128)]),
    ]:
        effects = []
        for block in range(1, 8):
            a, ac, b, bc = conditions[0]
            left, right = by_cell[(block, a, ac)], by_cell[(block, b, bc)]
            if left['status'] == right['status'] == 'estimated' and rail in left['joules_by_named_rail'] and rail in right['joules_by_named_rail']:
                effects.append(100 * (left['joules_by_named_rail'][rail] / right['joules_by_named_rail'][rail] - 1))
        contrasts.append({'rail': rail, 'contrast': kind, 'paired_blocks': len(effects),
            'block_effects_percent': effects,
            'median_percent': statistics.median(effects) if effects else None,
            'paired_block_bootstrap_95pct_percent': interval(effects, 20261017) if len(effects) >= 2 else None})
    interaction = []
    for block in range(1, 8):
        a, b, c, d = (by_cell[(block, 3500, 128)], by_cell[(block, 3500, 32)],
                      by_cell[(block, 3000, 128)], by_cell[(block, 3000, 32)])
        if all(x['status'] == 'estimated' and rail in x['joules_by_named_rail'] for x in (a,b,c,d)):
            interaction.append(100*(a['joules_by_named_rail'][rail]/b['joules_by_named_rail'][rail]-1)
                               -100*(c['joules_by_named_rail'][rail]/d['joules_by_named_rail'][rail]-1))
    contrasts.append({'rail': rail, 'contrast': 'cache_by_prefill_interaction_percentage_points',
        'paired_blocks': len(interaction), 'block_effects_percentage_points': interaction,
        'median_percentage_points': statistics.median(interaction) if interaction else None,
        'paired_block_bootstrap_95pct_percentage_points': interval(interaction, 20261018) if len(interaction) >= 2 else None})

cell_medians = []
for cache in (3000, 3500):
    for prefill in (32, 128):
        cell = [row for row in arms if row['cache_slots'] == cache and row['prefill_chunk'] == prefill]
        for rail in sorted({r for row in cell for r in row['joules_per_output_token_by_named_rail']}):
            values = [row['joules_per_output_token_by_named_rail'][rail] for row in cell
                      if row['status'] == 'estimated' and rail in row['joules_per_output_token_by_named_rail']]
            cell_medians.append({'cache_slots': cache, 'prefill_chunk': prefill, 'rail': rail,
                'estimated_blocks': len(values), 'median_joules_per_output_token': statistics.median(values) if values else None})

result = {'scope': 'Separate named tegrastats rails integrated over each API request window; includes board idle/background, is not process-attributed, and rails are not summed.',
    'method': 'Piecewise-linear integration of instantaneous mW at one-second wall timestamps; both request ends must be bracketed and gaps over 2.5 seconds are unsupported.',
    'planned_requests': len(arms), 'estimated_windows': sum(row['status'] == 'estimated' for row in arms),
    'unsupported_windows': sum(row['status'] != 'estimated' for row in arms),
    'per_cell_medians': cell_medians, 'paired_contrasts': contrasts, 'per_arm': arms}
(HERE / 'rail-energy.json').write_text(json.dumps(result, indent=2) + '\n')
with (HERE / 'rail-energy-pairs.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=['block','cache_slots','prefill_chunk','request_seconds','output_tokens','status','reason','joules_by_named_rail','joules_per_output_token_by_named_rail'], lineterminator='\n')
    writer.writeheader()
    for row in arms:
        writer.writerow(row)
print(json.dumps({'estimated_windows': result['estimated_windows'], 'unsupported_windows': result['unsupported_windows'],
                  'per_cell_medians': cell_medians, 'paired_contrasts': contrasts}, indent=2))
