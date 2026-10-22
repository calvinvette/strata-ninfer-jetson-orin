#!/usr/bin/env python3
"""Compare targeted full-vocabulary verifier logits at the first changed target position."""
import heapq
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent
HEADER = struct.Struct('<8sqiiiIQ')


def records(name):
    data = (ROOT / (name + '.bin')).read_bytes()
    result = []
    offset = 0
    while offset < len(data):
        magic, position, slot, row, token, _, vocab = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        logits = struct.unpack_from(f'<{vocab}f', data, offset)
        offset += vocab * 4
        if magic != b'STLOG01\0' or position != 127 or vocab != 248320:
            raise ValueError(f'{name}: unexpected record header')
        result.append({'position': position, 'slot': slot, 'row': row, 'input_token': token,
                       'logits': logits})
    if offset != len(data):
        raise ValueError(f'{name}: trailing or truncated record')
    return result


def select(name, slot=None, token=11, row=None):
    matches = [r for r in records(name) if r['input_token'] == token and
               (slot is None or r['slot'] == slot) and (row is None or r['row'] == row)]
    if len(matches) != 1:
        raise ValueError(f'{name}: expected one row for slot={slot} token={token} row={row}; got {len(matches)}')
    return matches[0]


def summarize(reference, candidate):
    a, b = reference['logits'], candidate['logits']
    deltas = [x - y for x, y in zip(a, b)]
    top_a = heapq.nlargest(5, enumerate(a), key=lambda pair: pair[1])
    top_b = heapq.nlargest(5, enumerate(b), key=lambda pair: pair[1])
    max_abs = max(abs(x) for x in deltas)
    l2 = math.sqrt(sum(x*x for x in deltas))
    norm = math.sqrt(sum(x*x for x in a))
    return {
        'reference': {'slot': reference['slot'], 'row': reference['row'], 'input_token': reference['input_token'],
                      'argmax': top_a[0][0], 'top5': [[i, v] for i, v in top_a],
                      'winner_margin': top_a[0][1] - top_a[1][1]},
        'candidate': {'slot': candidate['slot'], 'row': candidate['row'], 'input_token': candidate['input_token'],
                      'argmax': top_b[0][0], 'top5': [[i, v] for i, v in top_b],
                      'winner_margin': top_b[0][1] - top_b[1][1]},
        'delta': {'exact_values': sum(x != 0 for x in deltas), 'vocab': len(a), 'max_abs': max_abs,
                  'relative_l2': l2 / norm, 'mean_abs': sum(abs(x) for x in deltas) / len(deltas)},
    }

serial_target = select('run-position-127-logits/serial-target-only', token=11)
batch_target = select('run-position-127-logits-all-slots/batch-target-only', slot=1, token=11)
serial_mtp = select('run-position-127-logits/serial-mtp2', token=11)
batch_mtp = select('run-position-127-logits-all-slots/batch-mtp2', slot=1, token=11, row=0)
summary = {
    'capture': {'position': 127, 'prompt_slot': 1, 'input_token': 11, 'vocab': 248320},
    'serial_target_only_vs_two_row_target_batch': summarize(serial_target, batch_target),
    'serial_mtp2_vs_two_row_batch_mtp': summarize(serial_mtp, batch_mtp),
    'two_row_target_batch_vs_two_row_batch_mtp': summarize(batch_target, batch_mtp),
    'interpretation': 'At the same accepted input token, all three pairs differ numerically; the close top-two scores reverse rank. This localizes a logit row change at position 127 but does not identify its upstream operator or persistent-state source.'
}
(ROOT/'position-127-logit-analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({k: v['delta'] if 'delta' in v else v for k,v in summary.items() if k.endswith('batch') or k.endswith('mtp')}, indent=2))
