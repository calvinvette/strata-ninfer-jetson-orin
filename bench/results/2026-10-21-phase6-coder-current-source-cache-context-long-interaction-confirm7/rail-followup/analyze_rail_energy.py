#!/usr/bin/env python3
"""Retrospectively integrate named Orin rails over the measured API windows."""
from collections import defaultdict
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
for cell in sorted((BASE / 'per-cell-scopes').glob('block-*/*')):
    if not cell.is_dir() or not cell.name.startswith('cache'):
        continue
    # Original block 7 crossed local midnight and is explicitly excluded by
    # the campaign; the same-day replacement occupies block-07-replacement.
    if cell.parent.name == 'block-07':
        continue
    block = int(cell.parent.name.split('-')[1])
    cache = int(cell.name.split('-')[0].removeprefix('cache'))
    context = int(cell.name.split('-')[1].removeprefix('ctx'))
    requests = json.loads((cell / 'requests.json').read_text())
    measured = [x for x in requests['checks'] if not x.get('warmup')]
    if len(measured) != 1 or measured[0]['status'] != 'pass':
        raise RuntimeError(f'{cell}: expected exactly one passing measured request')
    request = measured[0]
    mem = [json.loads(x) for x in (cell / 'supervisor/memory.jsonl').read_text().splitlines()]
    if not mem:
        raise RuntimeError(f'{cell}: missing supervisor clock samples')
    offset = mem[0]['wall_time_s'] - mem[0]['monotonic_s']
    rails = rails_from_lines((cell / 'supervisor/tegrastats.txt').read_text().splitlines())
    estimate = window_energy(rails,
        request['request_start_monotonic_s'] + offset,
        request['request_end_monotonic_s'] + offset)
    if estimate['status'] != 'estimated':
        raise RuntimeError(f'{cell}: unsupported rail window: {estimate}')
    output_tokens = request['response']['usage']['completion_tokens']
    rows.append({
        'block': block, 'cache_mib': cache, 'context': context,
        'request_seconds': request['request_end_monotonic_s'] - request['request_start_monotonic_s'],
        'output_tokens': output_tokens,
        'joules_by_named_rail': estimate['joules_by_named_rail'],
        'joules_per_output_token_by_named_rail': {
            rail: joules / output_tokens for rail, joules in estimate['joules_by_named_rail'].items()},
        'telemetry_samples': len(rails), 'rail_scope': estimate['scope'],
        'integration_method': estimate['method'],
    })
if len(rows) != 28 or any(r['output_tokens'] != 48 for r in rows):
    raise RuntimeError(f'expected 28 passing 48-token measured windows, got {len(rows)}')

pairs, effects = [], []
for block in sorted({r['block'] for r in rows}):
    for context in (8192, 16384):
        by_cache = {r['cache_mib']: r for r in rows if r['block'] == block and r['context'] == context}
        if set(by_cache) != {1500, 3000}:
            raise RuntimeError(f'incomplete pair in block {block}, context {context}')
        a, b = by_cache[1500], by_cache[3000]
        common = sorted(set(a['joules_by_named_rail']) & set(b['joules_by_named_rail']))
        for rail in common:
            ratio = b['joules_per_output_token_by_named_rail'][rail] / a['joules_per_output_token_by_named_rail'][rail]
            pairs.append({'block': block, 'context': context, 'rail': rail,
                          'cache1500_j_per_token': a['joules_per_output_token_by_named_rail'][rail],
                          'cache3000_j_per_token': b['joules_per_output_token_by_named_rail'][rail],
                          'cache3000_over_cache1500_ratio': ratio})
for rail in sorted({p['rail'] for p in pairs}):
    for context in (8192, 16384):
        selected = [p for p in pairs if p['rail'] == rail and p['context'] == context]
        values = [p['cache3000_over_cache1500_ratio'] for p in selected]
        ci = interval(values, 20261021 + context + sum(map(ord, rail)))
        effects.append({'rail': rail, 'context': context, 'paired_blocks': len(values),
                        'cache1500_median_j_per_output_token': statistics.median(
                            p['cache1500_j_per_token'] for p in selected),
                        'cache3000_median_j_per_output_token': statistics.median(
                            p['cache3000_j_per_token'] for p in selected),
                        'median_cache3000_over_1500_change_percent': (statistics.median(values) - 1) * 100,
                        'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100]})
    by_block = {}
    for block in sorted({p['block'] for p in pairs}):
        ratios = {ctx: next(p['cache3000_over_cache1500_ratio'] for p in pairs
                            if p['rail'] == rail and p['context'] == ctx and p['block'] == block)
                  for ctx in (8192, 16384)}
        by_block[block] = ratios[16384] / ratios[8192]
    vals = list(by_block.values())
    ci = interval(vals, 20261021 + sum(map(ord, rail)))
    effects.append({'rail': rail, 'interaction': 'cache-by-context ratio-of-ratios', 'paired_blocks': len(vals),
                    'median_interaction_percent': (statistics.median(vals) - 1) * 100,
                    'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100]})

report = {
    'schema': 1,
    'source_campaign': '2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7',
    'scope': 'Retrospective integration of named tegrastats rail power over the existing measured API request windows; includes board idle/background activity, is not process-attributed, not summed across rails and not whole-device energy.',
    'method': 'Mapped each request monotonic interval to wall time using the first supervisor memory sample, then used the existing one-second piecewise-linear request_telemetry.window_energy integration. Windows require bracketing samples and no gaps over 2.5s.',
    'measured_windows': len(rows), 'unsupported_windows': 0, 'completion_tokens_each': 48,
    'factors': {'requested_expert_cache_mib': [1500, 3000], 'configured_context': [8192, 16384]},
    'request_windows': rows, 'paired_energy_per_token': pairs, 'paired_effects': effects,
}
out = Path(__file__).with_name('rail-energy-analysis.json')
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'measured_windows': len(rows), 'unsupported_windows': 0, 'effects': effects}, indent=2))
