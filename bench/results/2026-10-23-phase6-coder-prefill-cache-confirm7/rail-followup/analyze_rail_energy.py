#!/usr/bin/env python3
"""Integrate retained named Orin rails over held-out Coder request windows."""
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
    block = int(cell.parent.name.split('-')[1])
    cache = int(cell.name.split('-')[0].removeprefix('cache'))
    chunk = int(cell.name.split('-')[1].removeprefix('prefill'))
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
    estimate = window_energy(
        rails,
        request['request_start_monotonic_s'] + offset,
        request['request_end_monotonic_s'] + offset,
    )
    if estimate['status'] != 'estimated':
        raise RuntimeError(f'{cell}: unsupported rail window: {estimate}')
    output_tokens = request['response']['usage']['completion_tokens']
    rows.append({
        'block': block,
        'requested_expert_cache_slots': cache,
        'prefill_chunk': chunk,
        'request_seconds': request['request_end_monotonic_s'] - request['request_start_monotonic_s'],
        'output_tokens': output_tokens,
        'joules_by_named_rail': estimate['joules_by_named_rail'],
        'joules_per_output_token_by_named_rail': {
            rail: joules / output_tokens for rail, joules in estimate['joules_by_named_rail'].items()
        },
        'telemetry_samples': len(rails),
        'rail_scope': estimate['scope'],
        'integration_method': estimate['method'],
    })

if len(rows) != 28 or any(row['output_tokens'] != 46 for row in rows):
    raise RuntimeError(f'expected 28 passing 46-token measured windows, got {len(rows)}')

by_key = {(r['block'], r['requested_expert_cache_slots'], r['prefill_chunk']): r for r in rows}
if len(by_key) != 28:
    raise RuntimeError('duplicate measured block/cache/chunk key')
for block in range(1, 8):
    for cache in (1500, 3000):
        for chunk in (32, 128):
            if (block, cache, chunk) not in by_key:
                raise RuntimeError(f'missing cell block={block}, cache={cache}, chunk={chunk}')

rails = sorted(set.intersection(*(set(r['joules_per_output_token_by_named_rail']) for r in rows)))
effects = []
paired = []
for rail in rails:
    # Chunk effect at each requested cache capacity.
    for cache in (1500, 3000):
        ratios = []
        for block in range(1, 8):
            small = by_key[(block, cache, 32)]['joules_per_output_token_by_named_rail'][rail]
            large = by_key[(block, cache, 128)]['joules_per_output_token_by_named_rail'][rail]
            ratio = large / small
            ratios.append(ratio)
            paired.append({'rail': rail, 'block': block, 'contrast': 'chunk128_over_chunk32',
                           'requested_expert_cache_slots': cache, 'ratio': ratio,
                           'chunk32_j_per_output_token': small,
                           'chunk128_j_per_output_token': large})
        ci = interval(ratios, 2026102327 + cache + sum(map(ord, rail)))
        effects.append({
            'rail': rail,
            'contrast': 'chunk128_over_chunk32',
            'requested_expert_cache_slots': cache,
            'paired_blocks': len(ratios),
            'chunk32_median_j_per_output_token': statistics.median(
                by_key[(b, cache, 32)]['joules_per_output_token_by_named_rail'][rail] for b in range(1, 8)),
            'chunk128_median_j_per_output_token': statistics.median(
                by_key[(b, cache, 128)]['joules_per_output_token_by_named_rail'][rail] for b in range(1, 8)),
            'median_change_percent': (statistics.median(ratios) - 1) * 100,
            'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100],
        })
    # Difference-in-differences on within-block chunk ratios across cache levels.
    interaction = []
    for block in range(1, 8):
        ratio1500 = by_key[(block, 1500, 128)]['joules_per_output_token_by_named_rail'][rail] / by_key[(block, 1500, 32)]['joules_per_output_token_by_named_rail'][rail]
        ratio3000 = by_key[(block, 3000, 128)]['joules_per_output_token_by_named_rail'][rail] / by_key[(block, 3000, 32)]['joules_per_output_token_by_named_rail'][rail]
        interaction.append(ratio3000 / ratio1500)
    ci = interval(interaction, 2026102327 + sum(map(ord, rail)))
    effects.append({
        'rail': rail,
        'contrast': 'cache_by_chunk_ratio_of_ratios',
        'paired_blocks': len(interaction),
        'median_interaction_percent': (statistics.median(interaction) - 1) * 100,
        'paired_block_bootstrap_95_interval_percent': [(ci[0] - 1) * 100, (ci[1] - 1) * 100],
    })

report = {
    'schema': 1,
    'source_campaign': '2026-10-23-phase6-coder-prefill-cache-confirm7',
    'scope': ('Retrospective integration of named tegrastats rail power over measured API request windows; '
              'includes board idle/background activity, is not process-attributed, not summed across rails and '
              'not whole-device energy.'),
    'method': ('Mapped each request monotonic interval to wall time using the first supervisor memory sample, '
               'then used request_telemetry.window_energy piecewise-linear integration. Windows require bracketing '
               'samples and no gaps over 2.5 seconds. Bootstrap resamples paired blocks, not individual samples.'),
    'measured_windows': len(rows),
    'unsupported_windows': 0,
    'completion_tokens_each': 46,
    'factors': {'requested_expert_cache_slots': [1500, 3000], 'prefill_chunk': [32, 128]},
    'request_windows': rows,
    'paired_effects': effects,
    'paired_block_ratios': paired,
}
out = Path(__file__).with_name('rail-energy-analysis.json')
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'measured_windows': len(rows), 'unsupported_windows': 0, 'effects': effects}, indent=2))
