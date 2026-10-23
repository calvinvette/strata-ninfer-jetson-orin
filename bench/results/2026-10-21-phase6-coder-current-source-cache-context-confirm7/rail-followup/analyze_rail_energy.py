#!/usr/bin/env python3
"""Integrate named tegrastats rails over the short-task measured API windows."""
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
requests_out, cell_out = [], []
for block_dir in sorted((BASE / 'per-cell-scopes').glob('block-*')):
    block = int(block_dir.name.split('-')[1])
    for cell in sorted(block_dir.glob('cache*')):
        cache = int(cell.name.split('-')[0].removeprefix('cache'))
        request_data = json.loads((cell / 'requests.json').read_text())
        measured = [x for x in request_data['checks'] if not x.get('warmup')]
        if len(measured) != 3 or any(x['status'] != 'pass' for x in measured):
            raise RuntimeError(f'{cell}: expected three passing measured requests')
        mem = [json.loads(x) for x in (cell / 'supervisor/memory.jsonl').read_text().splitlines()]
        if not mem:
            raise RuntimeError(f'{cell}: missing supervisor clock samples')
        offset = mem[0]['wall_time_s'] - mem[0]['monotonic_s']
        rails = rails_from_lines((cell / 'supervisor/tegrastats.txt').read_text().splitlines())
        estimates = []
        for i, request in enumerate(measured):
            estimate = window_energy(rails,
                request['request_start_monotonic_s'] + offset,
                request['request_end_monotonic_s'] + offset)
            if estimate['status'] != 'estimated':
                raise RuntimeError(f'{cell} request {i}: unsupported rail window: {estimate}')
            tokens = request['response']['usage']['completion_tokens']
            if tokens != 47:
                raise RuntimeError(f'{cell} request {i}: expected 47 output tokens, got {tokens}')
            row = {'block': block, 'cache_mib': cache, 'request_index': i,
                   'request_seconds': request['request_end_monotonic_s'] - request['request_start_monotonic_s'],
                   'output_tokens': tokens, 'joules_by_named_rail': estimate['joules_by_named_rail'],
                   'joules_per_output_token_by_named_rail': {
                       rail: joules / tokens for rail, joules in estimate['joules_by_named_rail'].items()},
                   'rail_samples': len(rails), 'method': estimate['method']}
            requests_out.append(row)
            estimates.append(row)
        rails_common = set.intersection(*(set(x['joules_per_output_token_by_named_rail']) for x in estimates))
        cell_out.append({'block': block, 'cache_mib': cache, 'requests': len(estimates),
                         'median_joules_per_token_by_named_rail': {
                             rail: statistics.median(x['joules_per_output_token_by_named_rail'][rail]
                                                     for x in estimates)
                             for rail in sorted(rails_common)}})
if len(requests_out) != 42 or len(cell_out) != 14:
    raise RuntimeError(f'expected 42 request windows / 14 cells, got {len(requests_out)} / {len(cell_out)}')

pairs, summaries = [], []
for block in sorted({x['block'] for x in cell_out}):
    cells = {x['cache_mib']: x for x in cell_out if x['block'] == block}
    if set(cells) != {1500, 3000}:
        raise RuntimeError(f'incomplete block {block}')
    for rail in cells[1500]['median_joules_per_token_by_named_rail']:
        base = cells[1500]['median_joules_per_token_by_named_rail'][rail]
        candidate = cells[3000]['median_joules_per_token_by_named_rail'][rail]
        pairs.append({'block': block, 'rail': rail, 'cache1500_median_j_per_token': base,
                      'cache3000_median_j_per_token': candidate,
                      'cache3000_over_cache1500_ratio': candidate / base})
for rail in sorted({x['rail'] for x in pairs}):
    selected = [x for x in pairs if x['rail'] == rail]
    ratios = [x['cache3000_over_cache1500_ratio'] for x in selected]
    ci = interval(ratios, 2026102100 + sum(map(ord, rail)))
    summaries.append({'rail': rail, 'paired_blocks': len(ratios),
                      'cache1500_median_j_per_token': statistics.median(x['cache1500_median_j_per_token'] for x in selected),
                      'cache3000_median_j_per_token': statistics.median(x['cache3000_median_j_per_token'] for x in selected),
                      'median_change_percent': (statistics.median(ratios) - 1) * 100,
                      'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100]})

report = {'schema': 1,
 'source_campaign': '2026-10-21-phase6-coder-current-source-cache-context-confirm7',
 'scope': 'Named tegrastats rails integrated separately over 42 passing measured request windows; includes board idle/background activity, is not process-attributed, not summed and not whole-device energy.',
 'method': 'Each cell is the median of three per-output-token request-window rail integrals. Request monotonic times are mapped to wall time with the first supervisor memory sample; one-second piecewise-linear integration requires bracketing samples and no gaps over 2.5s.',
 'measured_windows': len(requests_out), 'unsupported_windows': 0,
 'factors': {'requested_expert_cache_mib': [1500, 3000], 'configured_context_tokens': 8192},
 'request_windows': requests_out, 'cell_medians': cell_out, 'paired_block_effects': pairs,
 'paired_summaries': summaries}
out = Path(__file__).with_name('rail-energy-analysis.json')
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'measured_windows': len(requests_out), 'unsupported_windows': 0,
                  'paired_summaries': summaries}, indent=2))
