#!/usr/bin/env python3
"""Join captured expert-132 service rows to same-input CPU/GPU expert oracles."""
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1]
RUNS = {
    'selector': BASE / 'layer21-position515-expert22-open-response-128pos',
    'no_selector': BASE / 'layer21-position515-open-response-direct-division-128pos',
}
HEADER = struct.Struct('<8sIIIIQq8i')


def metrics(a, b):
    delta = [float(y) - float(x) for x, y in zip(a, b)]
    return {
        'values': len(a),
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs_diff': max(map(abs, delta), default=0.0),
        'relative_l2': math.sqrt(sum(x*x for x in delta) / sum(float(x)*float(x) for x in a)) if any(a) else None,
        'left_sha256': hashlib.sha256(struct.pack(f'<{len(a)}f', *a)).hexdigest(),
        'right_sha256': hashlib.sha256(struct.pack(f'<{len(b)}f', *b)).hexdigest(),
    }


def captured_rows(path):
    data = path.read_bytes()
    out = []
    offset = 0
    while offset < len(data):
        fields = HEADER.unpack_from(data, offset)
        magic, version, layer, rows, k, width, pos0, *tokens = fields
        offset += HEADER.size
        if magic != b'STMPART1' or version != 1 or layer != 21:
            raise ValueError(f'invalid verifier-parts record at {offset - HEADER.size}')
        count = rows * k * width
        size = count * 4
        values = struct.unpack(f'<{count}f', data[offset:offset+size])
        offset += size
        for row in range(rows):
            if pos0 + row == 515:
                start = row * k * width + 9 * width
                out.append({'token_id': tokens[row], 'expert132': values[start:start+width]})
    if offset != len(data) or len(out) != 2:
        raise ValueError(f'expected two layer-21 rows at position 515, got {len(out)}')
    return out


oracle_cpu = struct.unpack('<2560f', (ROOT / 'oracle/layer-21-expert-132-cpu-output.f32').read_bytes())
oracle_gpu = struct.unpack('<2560f', (ROOT / 'oracle/layer-21-expert-132-gpu-output.f32').read_bytes())
result = {
    'scope': 'same-input native_expert_parity CPU/GPU oracle vs captured layer-21 expert-132 service rows',
    'activation_sha256': json.loads((ROOT / 'input.json').read_text())['activation_sha256'],
    'oracle_cpu_vs_gpu': metrics(oracle_cpu, oracle_gpu),
    'configurations': {},
}
for name, run in RUNS.items():
    rows = captured_rows(run / 'adaptive-cap8/result/verify-moe-parts.bin')
    routes = [json.loads(line) for line in (run / 'adaptive-cap8/result/all-layer-selected-positions.jsonl').read_text().splitlines()]
    routes = [r for r in routes if r.get('layer') == 21 and r.get('position') == 515]
    if len(routes) != 2 or len(routes[0]['ids']) <= 9 or routes[0]['ids'][9] != 132:
        raise ValueError(f'{name}: expected expert 132 at rank 9 in both captures')
    arms = []
    for i, (row, route) in enumerate(zip(rows, routes)):
        owner = route['route_kind'][9]
        oracle = oracle_cpu if owner == -1 else oracle_gpu
        arms.append({
            'token_id': row['token_id'],
            'owner_kind': owner,
            'oracle_owner': 'cpu' if owner == -1 else 'gpu',
            'service_vs_owner_oracle': metrics(oracle, row['expert132']),
            'service_vs_other_owner_oracle': metrics(oracle_gpu if owner == -1 else oracle_cpu, row['expert132']),
        })
    result['configurations'][name] = {'initial_recovery_token_ids_equal': rows[0]['token_id'] == rows[1]['token_id'], 'rows': arms}
out = ROOT / 'service-row-oracle-comparison.json'
out.write_text(json.dumps(result, indent=2) + '\n')
print(out)
for name, config in result['configurations'].items():
    print(name, [(row['oracle_owner'], row['service_vs_owner_oracle']['different_values'], row['service_vs_other_owner_oracle']['different_values']) for row in config['rows']])
