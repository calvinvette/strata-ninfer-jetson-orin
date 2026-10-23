#!/usr/bin/env python3
"""Integrate named Orin rails for the retained Q2 cache × prefill campaign."""
import gzip
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools' / 'integration'))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

BASE = Path(__file__).resolve().parents[1]
rows = []
unsupported = []
for cell in sorted(BASE.glob('block-*/*')):
    if not cell.is_dir():
        continue
    try:
        cache = int(cell.name.split('-')[0].removeprefix('cache'))
        chunk = int(cell.name.split('-')[1].removeprefix('prefill'))
        block = int(cell.parent.name.split('-')[1])
    except (IndexError, ValueError):
        continue
    request_data = json.loads((cell / 'requests.json').read_text())
    measured = [row for row in request_data['checks'] if not row.get('warmup')]
    if len(measured) != 1 or measured[0]['status'] != 'pass':
        raise RuntimeError(f'{cell}: expected exactly one passing measured request')
    request = measured[0]
    with gzip.open(cell / 'supervisor/memory.jsonl.gz', 'rt') as stream:
        memory = [json.loads(line) for line in stream if line.strip()]
    with gzip.open(cell / 'supervisor/tegrastats.txt.gz', 'rt') as stream:
        rails = rails_from_lines(stream)
    if not memory or not rails:
        unsupported.append({'block': block, 'cell': cell.name, 'reason': 'missing telemetry'})
        continue
    offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']
    estimate = window_energy(
        rails,
        request['request_start_monotonic_s'] + offset,
        request['request_end_monotonic_s'] + offset,
    )
    if estimate['status'] != 'estimated':
        unsupported.append({'block': block, 'cell': cell.name, **estimate})
        continue
    output_tokens = request['response']['usage']['completion_tokens']
    rows.append({
        'block': block, 'cache_slots': cache, 'prefill_chunk': chunk,
        'request_seconds': request['request_end_monotonic_s'] - request['request_start_monotonic_s'],
        'prompt_tokens': request['response']['usage']['prompt_tokens'],
        'completion_tokens': output_tokens,
        'total_tokens': request['response']['usage']['prompt_tokens'] + output_tokens,
        'joules_by_named_rail': estimate['joules_by_named_rail'],
        'joules_per_output_token_by_named_rail': {
            rail: joules / output_tokens for rail, joules in estimate['joules_by_named_rail'].items()},
        'joules_per_total_token_by_named_rail': {
            rail: joules / (request['response']['usage']['prompt_tokens'] + output_tokens)
            for rail, joules in estimate['joules_by_named_rail'].items()},
        'rail_samples': len(rails), 'integration_method': estimate['method'],
    })

if len(rows) != 28 or unsupported:
    raise RuntimeError(f'expected 28 supported windows; found {len(rows)}, unsupported={unsupported}')
if any(row['prompt_tokens'] != 7506 or row['completion_tokens'] != 41 for row in rows):
    raise RuntimeError('request token counts differ from the confirmed held-out workload')

paired = []
for block in sorted({row['block'] for row in rows}):
    cells = {(row['cache_slots'], row['prefill_chunk']): row for row in rows if row['block'] == block}
    if set(cells) != {(3000, 32), (3000, 128), (3500, 32), (3500, 128)}:
        raise RuntimeError(f'incomplete randomized block {block}')
    for factor, a_key, b_key in (
        ('cache', (3000, 32), (3500, 32)),
        ('cache', (3000, 128), (3500, 128)),
        ('prefill', (3000, 32), (3000, 128)),
        ('prefill', (3500, 32), (3500, 128)),
    ):
        a, b = cells[a_key], cells[b_key]
        for normalization, metric in (
            ('output_token', 'joules_per_output_token_by_named_rail'),
            ('all_prompt_and_output_tokens', 'joules_per_total_token_by_named_rail'),
        ):
            for rail in sorted(set(a[metric]) & set(b[metric])):
                paired.append({
                    'block': block, 'factor': factor, 'normalization': normalization, 'rail': rail,
                    'baseline': a_key, 'candidate': b_key,
                    'baseline_j_per_token': a[metric][rail],
                    'candidate_j_per_token': b[metric][rail],
                    'candidate_over_baseline_ratio': b[metric][rail] / a[metric][rail],
                })

effects = []
for factor in ('cache', 'prefill'):
    for normalization in ('output_token', 'all_prompt_and_output_tokens'):
        for rail in sorted({row['rail'] for row in paired}):
            for fixed in ((32, 128) if factor == 'cache' else (3000, 3500)):
                subset = [row for row in paired if row['factor'] == factor and
                          row['normalization'] == normalization and row['rail'] == rail and
                          row['baseline'][1 if factor == 'cache' else 0] == fixed]
                ratios = [row['candidate_over_baseline_ratio'] for row in subset]
                if len(ratios) != 7:
                    raise RuntimeError(f'incomplete paired effect for {factor}/{normalization}/{rail}/{fixed}')
                ci = interval(ratios, 20261018 + fixed + sum(map(ord, rail + normalization)))
                effects.append({
                    'factor': factor, 'normalization': normalization, 'rail': rail,
                    'fixed_prefill_chunk' if factor == 'cache' else 'fixed_cache_slots': fixed,
                    'paired_blocks': len(ratios),
                    'median_baseline_j_per_normalized_token': statistics.median(
                        row['baseline_j_per_token'] for row in subset),
                    'median_candidate_j_per_normalized_token': statistics.median(
                        row['candidate_j_per_token'] for row in subset),
                    'median_candidate_change_percent': (statistics.median(ratios) - 1) * 100,
                    'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100],
                })

interactions = []
for normalization in ('output_token', 'all_prompt_and_output_tokens'):
    for rail in sorted({row['rail'] for row in paired}):
        by_block = {}
        for block in sorted({row['block'] for row in rows}):
            lookup = {(row['factor'], row['baseline'], row['candidate']): row['candidate_over_baseline_ratio']
                      for row in paired if row['block'] == block and row['rail'] == rail and
                      row['normalization'] == normalization}
            cache_effects = [lookup[('cache', (3000, chunk), (3500, chunk))] for chunk in (32, 128)]
            prefill_effects = [lookup[('prefill', (cache, 32), (cache, 128))] for cache in (3000, 3500)]
            by_block[block] = {'cache_by_prefill_ratio_of_ratios': cache_effects[1] / cache_effects[0],
                               'prefill_by_cache_ratio_of_ratios': prefill_effects[1] / prefill_effects[0]}
        for interaction in ('cache_by_prefill_ratio_of_ratios', 'prefill_by_cache_ratio_of_ratios'):
            values = [value[interaction] for value in by_block.values()]
            ci = interval(values, 20261018 + sum(map(ord, rail + interaction + normalization)))
            interactions.append({
                'rail': rail, 'normalization': normalization, 'interaction': interaction,
                'paired_blocks': len(values),
                'median_ratio_of_ratios_change_percent': (statistics.median(values) - 1) * 100,
                'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100],
            })

report = {
    'schema': 1,
    'source_campaign': '2026-10-18-phase6-q2-cache-prefill-heldout-confirm7',
    'scope': ('Retrospective integration of named tegrastats rails over each measured API request. '
              'Includes board idle/background activity; not process-attributed, not summed across '
              'rails and not whole-device energy.'),
    'method': ('Mapped monotonic API request windows to wall time using the first supervisor memory '
               'sample and used request_telemetry.window_energy piecewise-linear integration. '
               'Windows require bracketing samples and no gaps over 2.5 seconds.'),
    'measured_windows': len(rows), 'unsupported_windows': unsupported,
    'blocks': 7, 'prompt_tokens_each': 7506, 'completion_tokens_each': 41,
    'factors': {'cache_slots': [3000, 3500], 'prefill_chunk': [32, 128]},
    'named_rail_request_windows': rows, 'paired_effects': effects, 'paired_interactions': interactions,
}
out = Path(__file__).with_name('rail-energy-analysis.json')
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'measured_windows': len(rows), 'unsupported_windows': len(unsupported),
                  'effects': effects, 'interactions': interactions}, indent=2))
