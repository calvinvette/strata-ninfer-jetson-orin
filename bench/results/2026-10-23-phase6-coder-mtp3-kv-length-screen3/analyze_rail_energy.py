#!/usr/bin/env python3
"""Integrate named tegrastats rails per request; preserve them as separate estimates."""
import csv
import json
import statistics
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'integration'))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

HERE = Path(__file__).resolve().parent
CAMPAIGN_ROOT = HERE / 'campaign'
campaign = json.loads((CAMPAIGN_ROOT / 'campaign.json').read_text())
runs = campaign['runs']
window = campaign['mtp_windows'][-1]
rows = []
for run in runs:
    run_dir = CAMPAIGN_ROOT / run['directory']
    request_data = json.loads((run_dir / 'requests.json').read_text())
    measured = [row for row in request_data['checks'] if not row.get('warmup')]
    if len(measured) != 1 or measured[0]['status'] != 'pass':
        raise RuntimeError(f"expected one passing measured request: {run['name']}")
    req = measured[0]
    memory = [json.loads(line) for line in (run_dir / 'supervisor/memory.jsonl').read_text().splitlines() if line]
    if not memory:
        raise RuntimeError(f"missing memory telemetry: {run['name']}")
    offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']
    rails = rails_from_lines((run_dir / 'supervisor/tegrastats.txt').read_text().splitlines())
    estimate = window_energy(rails, req['request_start_monotonic_s'] + offset,
                             req['request_end_monotonic_s'] + offset)
    metrics = run['metrics']
    output_tokens = metrics['completion_tokens']
    row = {'block': run['block'], 'kv': run['kv'], 'workload': run['workload'],
           'window': run['window'], 'run': run['name'], 'status': estimate['status'],
           'reason': estimate.get('reason'), 'request_seconds': req['request_end_monotonic_s'] - req['request_start_monotonic_s'],
           'output_tokens': output_tokens, 'scope': estimate.get('scope'),
           'method': estimate.get('method'),
           'joules_by_named_rail': estimate.get('joules_by_named_rail', {})}
    row['joules_per_output_token_by_named_rail'] = {
        rail: joules / output_tokens for rail, joules in row['joules_by_named_rail'].items()}
    rows.append(row)

by_key = {(row['block'], row['kv'], row['workload'], row['window']): row for row in rows}
pairs = []
for base in rows:
    if base['window'] != 0 or base['status'] != 'estimated':
        continue
    candidate = by_key.get((base['block'], base['kv'], base['workload'], window))
    if not candidate or candidate['status'] != 'estimated':
        continue
    common = set(base['joules_by_named_rail']) & set(candidate['joules_by_named_rail'])
    for rail in sorted(common):
        pairs.append({'block': base['block'], 'kv': base['kv'], 'workload': base['workload'],
                      'rail': rail, 'off_j': base['joules_by_named_rail'][rail],
                      'mtp_j': candidate['joules_by_named_rail'][rail],
                      'off_j_per_output_token': base['joules_per_output_token_by_named_rail'][rail],
                      'mtp_j_per_output_token': candidate['joules_per_output_token_by_named_rail'][rail],
                      'mtp_over_off_j_ratio': candidate['joules_by_named_rail'][rail] / base['joules_by_named_rail'][rail],
                      'mtp_over_off_j_per_token_ratio': candidate['joules_per_output_token_by_named_rail'][rail] / base['joules_per_output_token_by_named_rail'][rail]})

summaries = []
for kv in campaign['kv_formats']:
    for workload in campaign['workloads']:
        for rail in sorted({row['rail'] for row in pairs}):
            selected = [row for row in pairs if row['kv'] == kv and row['workload'] == workload and row['rail'] == rail]
            ratios = [row['mtp_over_off_j_per_token_ratio'] for row in selected]
            if not ratios:
                continue
            ci = interval(ratios, campaign['seed'] + len(summaries) * 37)
            summaries.append({'kv': kv, 'workload': workload, 'rail': rail,
                              'paired_blocks': len(selected),
                              'off_median_j_per_output_token': statistics.median(row['off_j_per_output_token'] for row in selected),
                              'mtp_median_j_per_output_token': statistics.median(row['mtp_j_per_output_token'] for row in selected),
                              'mtp_over_off_median_percent_change': (statistics.median(ratios) - 1) * 100,
                              'paired_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100]})

# Factor interactions use the per-block MTP/off energy-per-output-token ratio.
interactions = {'mtp_by_kv': [], 'mtp_by_workload': [], 'three_way': []}
for workload in campaign['workloads']:
    for rail in sorted({p['rail'] for p in pairs}):
        values = []
        # Derive ratio directly from the paired rows, indexed by treatment.
        for block in range(campaign['blocks']):
            fp = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == 'fp16' and p['workload'] == workload and p['rail'] == rail), None)
            i8 = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == 'int8' and p['workload'] == workload and p['rail'] == rail), None)
            if fp is not None and i8 is not None:
                values.append((i8 / fp - 1) * 100)
        if values:
            ci = interval(values, campaign['seed'] + 7000 + len(interactions['mtp_by_kv']))
            interactions['mtp_by_kv'].append({'workload': workload, 'rail': rail, 'paired_blocks': len(values),
                                               'median_interaction_percent': statistics.median(values),
                                               'paired_bootstrap_95_interval_percent': [(ci[0]), (ci[1])],
                                               'paired_values_percent': values})
for kv in campaign['kv_formats']:
    for rail in sorted({p['rail'] for p in pairs}):
        values = []
        for block in range(campaign['blocks']):
            short = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == kv and p['workload'] == campaign['workloads'][0] and p['rail'] == rail), None)
            long = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == kv and p['workload'] == campaign['workloads'][1] and p['rail'] == rail), None)
            if short is not None and long is not None:
                values.append((long / short - 1) * 100)
        if values:
            ci = interval(values, campaign['seed'] + 9000 + len(interactions['mtp_by_workload']))
            interactions['mtp_by_workload'].append({'kv': kv, 'rail': rail, 'paired_blocks': len(values),
                                                      'median_interaction_percent': statistics.median(values),
                                                      'paired_bootstrap_95_interval_percent': [ci[0], ci[1]],
                                                      'paired_values_percent': values})
for rail in sorted({p['rail'] for p in pairs}):
    values = []
    for block in range(campaign['blocks']):
        ratios = {}
        for kv in campaign['kv_formats']:
            for workload in campaign['workloads']:
                ratios[(kv, workload)] = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == kv and p['workload'] == workload and p['rail'] == rail), None)
        if all(v is not None for v in ratios.values()):
            values.append(((ratios[('int8', campaign['workloads'][1])] / ratios[('int8', campaign['workloads'][0])]) /
                           (ratios[('fp16', campaign['workloads'][1])] / ratios[('fp16', campaign['workloads'][0])]) - 1) * 100)
    if values:
        ci = interval(values, campaign['seed'] + 11000 + len(interactions['three_way']))
        interactions['three_way'].append({'rail': rail, 'paired_blocks': len(values),
                                          'median_interaction_percent': statistics.median(values),
                                          'paired_bootstrap_95_interval_percent': [ci[0], ci[1]],
                                          'paired_values_percent': values})

result = {'schema': 1,
          'scope': 'Named tegrastats rails integrated separately over API request windows. Includes idle/background activity; not process-attributed and no rails are summed.',
          'method': 'Piecewise-linear integration of one-second named mW samples; request windows without bracketing samples or with >2.5-second gaps are unsupported.',
          'candidate_window': window, 'attempted_windows': len(rows),
          'estimated_windows': sum(row['status'] == 'estimated' for row in rows),
          'unsupported_windows': [row for row in rows if row['status'] != 'estimated'],
          'request_estimates': rows, 'paired_estimates': pairs,
          'paired_summaries': summaries, 'interactions': interactions}
(HERE / 'rail-energy.json').write_text(json.dumps(result, indent=2) + '\n')
with (HERE / 'rail-energy-pairs.csv').open('w', newline='') as out:
    fields = list(pairs[0]) if pairs else ['block', 'kv', 'workload', 'rail']
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    writer.writeheader(); writer.writerows(pairs)
print(json.dumps({'estimated_windows': result['estimated_windows'],
                  'unsupported_windows': len(result['unsupported_windows']),
                  'summaries': summaries,
                  'interactions': interactions}, indent=2))
