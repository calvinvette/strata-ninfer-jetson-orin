#!/usr/bin/env python3
"""Map captured expert owner routes to fresh serial controls by activation."""
import argparse
import json
import math
from pathlib import Path

def read(path):
    rows = path.read_text().splitlines()
    if not rows or json.loads(rows[0]).get('format') != 'strata-moe-dispatch-v3':
        raise ValueError(f'{path}: not a strata-moe-dispatch-v3 capture')
    return [json.loads(row) for row in rows[1:]]

def distance(a, b):
    diff = [x - y for x, y in zip(a, b)]
    norm = max(math.fsum(x * x for x in a), 1e-300)
    return math.sqrt(math.fsum(x * x for x in diff) / norm)

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', type=Path, required=True)
a = p.parse_args()
serial = [read(a.run / f'serial-slot-{i}.owners.jsonl') for i in (0, 1)]
batch = read(a.run / 'batch.owners.jsonl')
results = []
for row in batch:
    if not row.get('activation_valid'):
        raise ValueError('cannot map batch row: no captured CPU-route activation')
    candidates = []
    for prompt, controls in enumerate(serial):
        for control in controls:
            if (control['layer'] == row['layer'] and control['position'] == row['position'] and
                    control['token_id'] == row['token_id'] and control.get('activation_valid') and
                    len(control['activation']) == len(row['activation'])):
                candidates.append((distance(control['activation'], row['activation']), prompt, control))
    if not candidates:
        raise ValueError(f"no serial activation for layer {row['layer']} position {row['position']}")
    candidates.sort(key=lambda x: x[0])
    delta, prompt, control = candidates[0]
    changes = []
    for rank, (serial_id, batch_id, serial_owner, batch_owner) in enumerate(zip(
            control['ids'], row['ids'], control['route_kind'], row['route_kind'])):
        if serial_id != batch_id or serial_owner != batch_owner:
            changes.append({'rank': rank, 'serial_expert': serial_id, 'batch_expert': batch_id,
                            'serial_owner': serial_owner, 'batch_owner': batch_owner})
    results.append({'layer': row['layer'], 'position': row['position'], 'token': row['token_id'],
                    'batch_dispatch': row['dispatch'], 'serial_prompt': prompt,
                    'activation_relative_l2': delta, 'route_ids_exact': control['ids'] == row['ids'],
                    'owner_changes': changes})
print(json.dumps({'owner_codes': {'-1': 'CPU', '0': 'primary VRAM', '1': 'PCIe', '2': 'peer/helper GPU'},
                  'records': results}, indent=2))
