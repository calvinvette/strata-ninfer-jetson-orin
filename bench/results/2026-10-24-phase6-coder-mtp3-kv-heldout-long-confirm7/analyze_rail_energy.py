#!/usr/bin/env python3
"""Integrate named Orin rails over held-out MTP x KV request windows."""
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'integration'))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

HERE = Path(__file__).resolve().parent
CAMPAIGN_ROOT = HERE / 'campaign'
campaign = json.loads((CAMPAIGN_ROOT / 'campaign.json').read_text())
window = max(campaign['mtp_windows'])
rows = []
for run in campaign['runs']:
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
    tokens = run['metrics']['completion_tokens']
    row = {'block': run['block'], 'kv': run['kv'], 'workload': run['workload'],
           'window': run['window'], 'run': run['name'], 'status': estimate['status'],
           'reason': estimate.get('reason'), 'request_seconds': req['request_end_monotonic_s'] - req['request_start_monotonic_s'],
           'output_tokens': tokens, 'scope': estimate.get('scope'), 'method': estimate.get('method'),
           'joules_by_named_rail': estimate.get('joules_by_named_rail', {})}
    row['joules_per_output_token_by_named_rail'] = {
        rail: joules / tokens for rail, joules in row['joules_by_named_rail'].items()}
    rows.append(row)

by_key = {(r['block'], r['kv'], r['workload'], r['window']): r for r in rows}
pairs = []
for base in rows:
    if base['window'] != 0 or base['status'] != 'estimated':
        continue
    candidate = by_key.get((base['block'], base['kv'], base['workload'], window))
    if not candidate or candidate['status'] != 'estimated':
        continue
    for rail in sorted(set(base['joules_by_named_rail']) & set(candidate['joules_by_named_rail'])):
        off = base['joules_per_output_token_by_named_rail'][rail]
        mtp = candidate['joules_per_output_token_by_named_rail'][rail]
        pairs.append({'block': base['block'], 'kv': base['kv'], 'rail': rail,
                      'off_j': base['joules_by_named_rail'][rail],
                      'mtp_j': candidate['joules_by_named_rail'][rail],
                      'off_j_per_output_token': off, 'mtp_j_per_output_token': mtp,
                      'mtp_over_off_j_per_token_ratio': mtp / off})

summaries = []
for kv in campaign['kv_formats']:
    for rail in sorted({p['rail'] for p in pairs}):
        selected = [p for p in pairs if p['kv'] == kv and p['rail'] == rail]
        ratios = [p['mtp_over_off_j_per_token_ratio'] for p in selected]
        if not ratios:
            continue
        ci = interval(ratios, campaign['seed'] + len(summaries) * 37)
        summaries.append({'kv': kv, 'workload': campaign['workloads'][0], 'rail': rail,
                          'paired_blocks': len(selected),
                          'off_median_j_per_output_token': statistics.median(p['off_j_per_output_token'] for p in selected),
                          'mtp_median_j_per_output_token': statistics.median(p['mtp_j_per_output_token'] for p in selected),
                          'mtp_over_off_median_percent_change': (statistics.median(ratios) - 1) * 100,
                          'paired_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100],
                          'paired_ratios': ratios})

interactions = []
for rail in sorted({p['rail'] for p in pairs}):
    values = []
    for block in range(campaign['blocks']):
        fp = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == 'fp16' and p['rail'] == rail), None)
        i8 = next((p['mtp_over_off_j_per_token_ratio'] for p in pairs if p['block'] == block and p['kv'] == 'int8' and p['rail'] == rail), None)
        if fp is not None and i8 is not None:
            values.append((i8 / fp - 1) * 100)
    if values:
        ci = interval(values, campaign['seed'] + 7000 + len(interactions))
        interactions.append({'rail': rail, 'paired_blocks': len(values),
                             'median_mtp_by_kv_interaction_percent': statistics.median(values),
                             'paired_bootstrap_95_interval_percent': ci,
                             'paired_values_percent': values})

result = {'schema': 1,
          'scope': 'Named tegrastats rails integrated separately over API request windows; includes idle/background activity and is not process-attributed. Rails are not summed.',
          'method': 'Piecewise-linear integration of one-second named mW samples; request windows without bracketing samples or with >2.5-second gaps are unsupported.',
          'candidate_window': window, 'attempted_windows': len(rows),
          'estimated_windows': sum(r['status'] == 'estimated' for r in rows),
          'unsupported_windows': [r for r in rows if r['status'] != 'estimated'],
          'request_estimates': rows, 'paired_estimates': pairs,
          'paired_summaries': summaries, 'mtp_by_kv_interactions': interactions}
(HERE / 'rail-energy.json').write_text(json.dumps(result, indent=2) + '\n')
with (HERE / 'rail-energy-pairs.csv').open('w', newline='') as out:
    fields = list(pairs[0]) if pairs else ['block', 'kv', 'rail']
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    writer.writeheader(); writer.writerows(pairs)
print(json.dumps({'estimated_windows': result['estimated_windows'],
                  'unsupported_windows': len(result['unsupported_windows']),
                  'summaries': summaries, 'interactions': interactions}, indent=2))
