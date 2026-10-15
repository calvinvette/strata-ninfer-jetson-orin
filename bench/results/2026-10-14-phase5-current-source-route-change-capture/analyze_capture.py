#!/usr/bin/env python3
"""Compare aligned initial/recovery expert-dispatch rows without retaining token text."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
run = ROOT / 'bench/results/2026-10-14-phase5-current-source-route-change-capture/run'
records = [json.loads(line) for line in (run / 'start-0.jsonl').read_text().splitlines()]
assert records[0]['format'] == 'strata-moe-dispatch-v2' and records[0]['n_embd'] == 2560
rows = records[1:]
assert len(rows) == 66, f'expected three requests x 22 rows, got {len(rows)}'
initial, long_request, recovery = rows[:22], rows[22:44], rows[44:66]
assert [initial[0]['dispatch'], long_request[0]['dispatch'], recovery[0]['dispatch']] == [0, 912, 1824]
assert [initial[0]['stream_row'], long_request[0]['stream_row'], recovery[0]['stream_row']] == [0, 22, 44]
exact_activation = sum(a['activation'] == b['activation'] for a, b in zip(initial, recovery))
exact_ids = sum(a['ids'] == b['ids'] for a, b in zip(initial, recovery))
exact_owners = sum(a['route_kind'] == b['route_kind'] for a, b in zip(initial, recovery))
route_flips = []
for row, (a, b) in enumerate(zip(initial[:7], recovery[:7])):
    assert a['activation'] == b['activation'] and a['ids'] == b['ids']
    flips = [{'expert': e, 'from': x, 'to': y} for e, x, y in zip(a['ids'], a['route_kind'], b['route_kind']) if x != y]
    route_flips.append({'row': row, 'expert_ids': a['ids'], 'flips': flips})
assert all(len(item['flips']) > 0 for item in route_flips)
assert all(initial[i]['activation'] != recovery[i]['activation'] for i in range(7, 22))
num = den = max_abs = 0.0
for a, b in zip(initial[7:], recovery[7:]):
    for x, y in zip(a['activation'], b['activation']):
        num += (x - y) ** 2
        den += x ** 2
        max_abs = max(max_abs, abs(x - y))
rows_result = {
    'format': records[0]['format'], 'layer': 0, 'model': 'Qwen3.8-Flash-Next Coder IQ1_M',
    'mtp': 0, 'sequence': ['short-512', 'long-2048', 'short-512-recovery'],
    'capture_rows_per_request': [len(initial), len(long_request), len(recovery)],
    'aligned_initial_vs_recovery_rows': 22,
    'activation_exact_rows': exact_activation, 'expert_ids_exact_rows': exact_ids,
    'owner_exact_rows': exact_owners,
    'first_seven_rows_same_activation_and_ids_all_changed_owner': True,
    'route_owner_flips_in_first_seven_rows': sum(len(item['flips']) for item in route_flips),
    'route_owner_flip_details': route_flips,
    'later_rows_with_different_activation': 15,
    'later_rows_with_different_expert_ids': sum(initial[i]['ids'] != recovery[i]['ids'] for i in range(7, 22)),
    'later_activation_relative_l2': math.sqrt(num / den), 'later_activation_max_abs': max_abs,
    'same_activation_example': {'stream_row_initial': 0, 'stream_row_recovery': 44,
                                'expert_119_owner_initial': initial[0]['route_kind'][2],
                                'expert_119_owner_recovery': recovery[0]['route_kind'][2]},
    'source_capture_sha256': __import__('hashlib').sha256((run / 'start-0.jsonl').read_bytes()).hexdigest(),
}
out = run / 'route-analysis.json'
out.write_text(json.dumps(rows_result, indent=2) + '\n')
print(json.dumps(rows_result, indent=2))
