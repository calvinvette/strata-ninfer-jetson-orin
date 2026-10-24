#!/usr/bin/env python3
"""Pair batch QSA state hashes with serial accepted-prefix hashes."""
import argparse
import json
import re
from itertools import permutations
from pathlib import Path


def serial_records(path: Path) -> dict[int, dict]:
    layer_re = re.compile(r'qsa=(\d+) layer=(\d+) hash=([0-9a-f]{16}) idx=([0-9a-f]{16}) kv=([0-9a-f]{16})')
    length_re = re.compile(r'STATE_HASH_QSA_LAYERS L=(\d+)')
    accepted_re = re.compile(r'ACCEPTED_PREFIX position=(\d+).*?tokens=([0-9,]+)')
    records = {}
    tokens = {}
    for line in path.read_text(errors='replace').splitlines():
        accepted = accepted_re.search(line)
        if accepted:
            values = [int(value) for value in accepted.group(2).split(',')]
            if len(values) == 1:
                tokens[int(accepted.group(1))] = values[0]
        length = length_re.search(line)
        if not length:
            continue
        rows = layer_re.findall(line)
        if not rows:
            continue
        records[int(length.group(1)) - 1] = {
            key: [row[index] for row in rows]
            for key, index in [('hashes', 2), ('idx_hashes', 3), ('kv_hashes', 4)]
        }
        records[int(length.group(1)) - 1]['layers'] = [int(row[1]) for row in rows]
    for position, record in records.items():
        record['token'] = tokens.get(position)
    return records


def batch_records(path: Path) -> dict[int, list[dict]]:
    result = {0: [], 1: []}
    for line in path.read_text().splitlines():
        if not line:
            continue
        fields = dict(re.findall(r'(\w+)=([^ ]+)', line))
        slot = int(fields['slot'])
        if slot not in result:
            continue
        hashes = line.split('hashes=', 1)[1].split(' idx_hashes=', 1)[0].split()
        idx_hashes = line.split('idx_hashes=', 1)[1].split(' kv_hashes=', 1)[0].split()
        kv_hashes = line.split('kv_hashes=', 1)[1].split()
        result[slot].append({'position': int(fields['position']), 'token': int(fields['token']),
                             'hashes': hashes, 'idx_hashes': idx_hashes, 'kv_hashes': kv_hashes})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    serial = {slot: serial_records(args.run / f'serial-slot-{slot}.log') for slot in (0, 1)}
    batch = batch_records(args.run / 'batch.batch-qsa-hashes.txt')
    assignments = []
    for controls in permutations((0, 1)):
        total, mapping = 0, {}
        for slot, control in enumerate(controls):
            scores = {offset: sum(
                record['token'] == serial[control].get(record['position'] - offset, {}).get('token')
                and record['hashes'] == serial[control].get(record['position'] - offset, {}).get('hashes')
                for record in batch[slot]) for offset in range(9)}
            best = max(scores, key=lambda k: (scores[k], -k))
            mapping[slot] = {'serial_control': control, 'position_offset': best,
                             'alignment_scores': scores, 'exact_alignment_count': scores[best]}
            total += scores[best]
        assignments.append((total, controls, mapping))
    assignments.sort(key=lambda row: row[0], reverse=True)
    if not assignments or assignments[0][0] == 0 or (
            len(assignments) > 1 and assignments[0][0] == assignments[1][0]):
        raise ValueError(f'ambiguous QSA slot/control alignment: {[row[0] for row in assignments]}')

    result = {'scope': 'batch QSA indexer/KV state hashes paired to serial accepted-prefix states',
              'slot_mapping': {}, 'slots': {}}
    for slot in (0, 1):
        control = assignments[0][2][slot]['serial_control']
        offset = assignments[0][2][slot]['position_offset']
        compared = []
        for record in batch[slot]:
            expected = serial[control].get(record['position'] - offset)
            if expected is None:
                continue
            if record['token'] != expected['token']:
                raise ValueError(f'slot {slot}: token alignment mismatch at batch position {record["position"]}')
            different = {}
            for key in ('hashes', 'idx_hashes', 'kv_hashes'):
                if len(record[key]) != len(expected[key]):
                    raise ValueError(f'slot {slot} {key} length mismatch')
                different[key] = [i for i, (x, y) in enumerate(zip(expected[key], record[key])) if x != y]
            compared.append({'batch_position': record['position'],
                             'serial_prefix_position': record['position'] - offset,
                             'token_id': record['token'],
                             'exact': not any(different.values()),
                             'different_qsa_ordinals': different,
                             'different_model_layers': {
                                 key: [expected['layers'][i] for i in ids]
                                 for key, ids in different.items()}})
        first = next((row for row in compared if not row['exact']), None)
        result['slot_mapping'][str(slot)] = assignments[0][2][slot]
        result['slots'][str(slot)] = {'compared_positions': len(compared),
                                      'exact_positions': sum(row['exact'] for row in compared),
                                      'first_mismatch': first,
                                      'records': compared}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({slot: {'compared': data['compared_positions'],
                             'exact': data['exact_positions'],
                             'first_mismatch': data['first_mismatch']}
                      for slot, data in result['slots'].items()}, indent=2))


if __name__ == '__main__':
    main()
