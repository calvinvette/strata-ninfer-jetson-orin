#!/usr/bin/env python3
"""Pair batch per-layer GDN hashes with serial accepted-prefix state hashes."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run-gdn-hash-sweep'


def serial_segments(path):
    segments = [{}]
    pending = None
    text = Path(path).read_text(errors='replace')
    for line in text.splitlines():
        if 'STATE_HASH_GDN ' in line:
            pending = line.split('STATE_HASH_GDN ', 1)[1].split()
        match = re.search(r'ACCEPTED_PREFIX position=\d+ .*?state=\{STATE_HASH L=(\d+)', line)
        if match and pending is not None:
            segments[-1][int(match.group(1))] = pending
            pending = None
        if 'strata serve: prompt 68 tokens =' in line and len(segments) < 2:
            segments.append({})
    return segments


def batch_records(name):
    result = []
    for line in (RUN / (name + '-gdn-hashes.txt')).read_text().splitlines():
        match = re.fullmatch(r'position=(\d+) slot=(\d+) row=(\d+) layers=(\d+) hashes=(.*)', line)
        if not match:
            raise ValueError(f'{name}: malformed batch hash line: {line[:100]}')
        result.append({'position': int(match.group(1)), 'slot': int(match.group(2)),
                       'row': int(match.group(3)), 'layers': int(match.group(4)),
                       'hashes': match.group(5).split()})
    return result


def analyze(label, serial_name, batch_name):
    prompt0 = serial_segments(RUN / (serial_name + '.log'))[0]
    prompt1 = serial_segments(ROOT / 'run-isolated-prompt1-gdn' / (serial_name.replace('serial-', '') + '.log'))[0]
    serial = [prompt0, prompt1]
    records = batch_records(batch_name)
    per_slot = {}
    for item in records:
        position = item['position']
        candidates = []
        for prompt, states in enumerate(serial):
            ref = states.get(position)
            if ref is not None:
                differing = [i for i, (a, b) in enumerate(zip(item['hashes'], ref)) if a != b]
                candidates.append({'prompt': prompt, 'different_layers': differing})
        if not candidates:
            continue
        best = min(candidates, key=lambda x: len(x['different_layers']))
        per_slot.setdefault(str(item['slot']), []).append({
            'position': position, 'row': item['row'], 'closest_prompt': best['prompt'],
            'changed_layers': best['different_layers'],
        })
    compact = {}
    for slot, items in per_slot.items():
        exact = next((x for x in items if not x['changed_layers']), None)
        mapping = exact['closest_prompt'] if exact else None
        paired = [x for x in items if mapping is not None and x['closest_prompt'] == mapping]
        first_drift = next((x for x in paired if x['changed_layers']), None)
        compact[slot] = {
            'row_count': len(items),
            'request_mapping_from_first_exact': ({'prompt': mapping, 'position': exact['position'],
                                                   'row': exact['row']} if exact else None),
            'exact_positions': [x['position'] for x in paired if not x['changed_layers']],
            'first_nonexact_position_after_mapping': first_drift,
            'compared_positions': [x['position'] for x in paired],
            'positions_without_serial_committed_hash': len(records) - len(items),
            'unmapped_nearest_comparison': (None if mapping is not None else items[0]),
        }
    return {'serial_positions': [len(s) for s in serial], 'batch_hash_rows': len(records),
            'slots': compact}


summary = {
    'target-only': analyze('target-only', 'serial-target-only', 'batch-target-only'),
    'mtp2': analyze('mtp2', 'serial-mtp2', 'batch-mtp2'),
    'limits': [
        'A missing committed position means the serial arm committed a multi-token MTP window and did not emit a hash at that intermediate length.',
        'Layer indices are GDN-state ordinals, not model layer numbers.',
        'Batch slot assignment is resolved by exact state hashes; it is not assumed stable across runs.',
    ],
}
(ROOT / 'gdn-hash-sweep-analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({name: {'slots': arm['slots'],
                         'rows': arm['batch_hash_rows']}
                   for name, arm in summary.items() if name in ('target-only', 'mtp2')}, indent=2))
