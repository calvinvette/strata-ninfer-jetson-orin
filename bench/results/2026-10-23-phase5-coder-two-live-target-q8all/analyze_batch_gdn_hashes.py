#!/usr/bin/env python3
"""Align per-slot batch GDN hashes to serial accepted-prefix hashes."""
import argparse
from itertools import permutations
import json
import re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = a.run
state_re = re.compile(r'STATE_HASH_GDN ((?:[0-9a-f]{16} ?)+)')
accepted_re = re.compile(r'ACCEPTED_PREFIX position=(\d+)')
serial = {}
for slot in (0, 1):
    lines = (root / f'serial-slot-{slot}.log').read_text(errors='replace').splitlines()
    accepted_position = None
    serial[slot] = {}
    for line in lines:
        match = accepted_re.search(line)
        if match:
            accepted_position = int(match.group(1))
        match = state_re.search(line)
        if match and accepted_position is not None:
            serial[slot][accepted_position] = match.group(1).split()

batch = {0: [], 1: []}
for line in (root / 'batch.batch-gdn-hashes.txt').read_text().splitlines():
    prefix, hashes = line.split('hashes=', 1)
    fields = dict(item.split('=', 1) for item in prefix.split())
    slot = int(fields['slot'])
    if slot not in batch:
        continue
    batch[slot].append({'position': int(fields['position']), 'hashes': hashes.split()})

def score(slot, control, offset):
    return sum(1 for record in batch[slot]
               if record['position'] - offset in serial[control]
               and record['hashes'] == serial[control][record['position'] - offset])

assignments = []
for controls in permutations((0, 1)):
    per_slot = {}
    total = 0
    for slot, control in enumerate(controls):
        by_offset = {offset: score(slot, control, offset) for offset in range(0, 9)}
        offset = max(by_offset, key=lambda value: (by_offset[value], -value))
        per_slot[slot] = {'serial_control': control, 'offset': offset,
                          'scores': by_offset, 'matches': by_offset[offset]}
        total += by_offset[offset]
    assignments.append((total, controls, per_slot))
assignments.sort(key=lambda item: item[0], reverse=True)
if not assignments or assignments[0][0] == 0:
    raise ValueError('no exact per-layer GDN hash alignment found')
if len(assignments) > 1 and assignments[0][0] == assignments[1][0]:
    raise ValueError(f'ambiguous batch-slot to serial-prompt mapping: scores {assignments[0][0]} and {assignments[1][0]}')
_, _, mapping = assignments[0]

result = {'scope': 'per-layer hashes of allocated GDN state; batch slots paired to serial prompts by exact hashes',
          'slot_mapping': {}, 'slots': {}}
for slot in (0, 1):
    records = batch[slot]
    control = mapping[slot]['serial_control']
    offset = mapping[slot]['offset']
    exact_positions = []
    first_mismatch = None
    compared = 0
    for record in records:
        serial_position = record['position'] - offset
        expected = serial[control].get(serial_position)
        if expected is None:
            continue
        compared += 1
        different = [i for i, (x, y) in enumerate(zip(expected, record['hashes'])) if x != y]
        if not different:
            exact_positions.append({'batch_position': record['position'], 'serial_prefix_position': serial_position})
        elif first_mismatch is None:
            first_mismatch = {'batch_position': record['position'],
                              'serial_prefix_position': serial_position,
                              'first_gdn_allocation_ordinal': different[0],
                              'different_gdn_allocations': len(different),
                              'total_gdn_allocations': min(len(expected), len(record['hashes']))}
    result['slot_mapping'][str(slot)] = {
        'serial_control': control,
        'inferred_position_offset': offset,
        'exact_alignment_count_by_candidate_offset': {str(k): v for k, v in mapping[slot]['scores'].items()},
        'compared_positions': compared,
        'exact_positions': exact_positions,
    }
    result['slots'][str(slot)] = {
        'serial_control': control,
        'inferred_position_offset': offset,
        'compared_positions': compared,
        'exact_positions': exact_positions,
        'first_mismatch': first_mismatch,
    }
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({slot: {'offset': data['inferred_position_offset'],
                         'compared': data['compared_positions'],
                         'first_mismatch': data['first_mismatch']}
                  for slot, data in result['slots'].items()}, indent=2))
