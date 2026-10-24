#!/usr/bin/env python3
"""Integrate per-request named Orin rails and paired worker/transfer effects."""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'integration'))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

HERE = Path(__file__).resolve().parent
campaign = json.loads((HERE / 'campaign/results.json').read_text())
observations = rails_from_lines((HERE / 'supervisor/tegrastats.txt').read_text().splitlines())
memory = [json.loads(line) for line in (HERE / 'supervisor/memory.jsonl').read_text().splitlines() if line]
if not memory:
    raise RuntimeError('missing supervisor time base')
offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']

rows = []
for run in campaign['runs']:
    request_data = json.loads((HERE / 'campaign' / run['request_file']).read_text())
    measured = [row for row in request_data['checks'] if not row.get('warmup')]
    if len(measured) != 1 or measured[0]['status'] != 'pass':
        raise RuntimeError(f"expected one passing request: block {run['repetition']}")
    request = measured[0]
    estimate = window_energy(
        observations,
        request['request_start_monotonic_s'] + offset,
        request['request_end_monotonic_s'] + offset,
    )
    row = {
        'block': run['repetition'], 'workers': run['workers'],
        'transfer_mode': run['transfer_mode'], 'status': estimate['status'],
        'reason': estimate.get('reason'), 'request_seconds': run['request_ms'] / 1000,
        'output_tokens': run['generated_tokens'], 'scope': estimate.get('scope'),
        'method': estimate.get('method'),
        'joules_by_named_rail': estimate.get('joules_by_named_rail', {}),
    }
    row['joules_per_output_token_by_named_rail'] = {
        rail: joules / row['output_tokens']
        for rail, joules in row['joules_by_named_rail'].items()
    }
    rows.append(row)

if any(row['status'] != 'estimated' for row in rows):
    raise RuntimeError('one or more request windows lack supported rail estimates')

cell = {(r['block'], r['workers'], r['transfer_mode']): r for r in rows}
effects = {'worker_4_vs_8_percent_by_transfer': {},
           'pread_vs_mapped_percent_by_workers': {}, 'interaction_pp': {}}
rails = sorted(rows[0]['joules_per_output_token_by_named_rail'])
for rail in rails:
    worker_values, transfer_values, interaction = {}, {}, []
    for mode in ('mapped', 'pread'):
        values = []
        for block in range(campaign['planned_repetitions']):
            four = cell[(block, 4, mode)]['joules_per_output_token_by_named_rail'][rail]
            eight = cell[(block, 8, mode)]['joules_per_output_token_by_named_rail'][rail]
            values.append((four / eight - 1) * 100)
        worker_values[mode] = values
        ci = interval(values, campaign['seed'] + 1000 + len(effects['worker_4_vs_8_percent_by_transfer']))
        effects['worker_4_vs_8_percent_by_transfer'].setdefault(rail, {})[mode] = {
            'paired_values': values, 'median_percent': statistics.median(values),
            'bootstrap_95pct_median_interval': ci,
        }
    for workers in (4, 8):
        values = []
        for block in range(campaign['planned_repetitions']):
            mapped = cell[(block, workers, 'mapped')]['joules_per_output_token_by_named_rail'][rail]
            pread = cell[(block, workers, 'pread')]['joules_per_output_token_by_named_rail'][rail]
            values.append((pread / mapped - 1) * 100)
        transfer_values[str(workers)] = values
        ci = interval(values, campaign['seed'] + 2000 + len(effects['pread_vs_mapped_percent_by_workers']))
        effects['pread_vs_mapped_percent_by_workers'].setdefault(rail, {})[str(workers)] = {
            'paired_values': values, 'median_percent': statistics.median(values),
            'bootstrap_95pct_median_interval': ci,
        }
    for block in range(campaign['planned_repetitions']):
        interaction.append(transfer_values['4'][block] - transfer_values['8'][block])
    ci = interval(interaction, campaign['seed'] + 3000 + len(effects['interaction_pp']))
    effects['interaction_pp'][rail] = {
        'paired_values': interaction, 'median_percentage_points': statistics.median(interaction),
        'bootstrap_95pct_median_interval': ci,
    }

summary = {}
for workers in (4, 8):
    summary[str(workers)] = {}
    for mode in ('mapped', 'pread'):
        selected = [r for r in rows if r['workers'] == workers and r['transfer_mode'] == mode]
        summary[str(workers)][mode] = {
            'samples': len(selected), 'median_joules_per_output_token_by_named_rail': {
                rail: statistics.median(r['joules_per_output_token_by_named_rail'][rail] for r in selected)
                for rail in rails
            },
        }

result = {
    'schema': 1,
    'scope': 'Named tegrastats rails integrated over API request windows; readings include idle/background activity and are not process-attributed. Rails are not summed.',
    'method': 'Piecewise-linear integration of one-second named power samples; request windows without bracketing samples or with >2.5-second gaps are unsupported.',
    'estimated_windows': len(rows), 'unsupported_windows': [], 'request_estimates': rows,
    'cell_medians_joules_per_output_token': summary,
    'paired_effects_percent': effects,
}
(HERE / 'named-rail-energy.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'estimated_windows': len(rows), 'summary': summary,
                  'paired_effects_percent': effects}, indent=2))
