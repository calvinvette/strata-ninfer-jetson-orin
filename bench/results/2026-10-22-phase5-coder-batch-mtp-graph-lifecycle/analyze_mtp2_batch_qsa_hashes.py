#!/usr/bin/env python3
"""Pair per-QSA batch MTP hashes with serial accepted-prefix hashes."""
import argparse
import json
import re
from pathlib import Path


def serial_prefixes(path):
    result = {}
    current = None
    for line in path.read_text(errors='replace').splitlines():
        match = re.search(r'STATE_HASH_QSA_LAYERS L=(\d+) (.*)', line)
        if match:
            hashes = re.findall(r'qsa=(\d+) layer=(\d+) hash=([0-9a-f]+)', match.group(2))
            current = (int(match.group(1)), [row[2] for row in hashes])
            continue
        match = re.search(r'ACCEPTED_PREFIX position=(\d+).*tokens=([0-9,]+) state=\{STATE_HASH L=(\d+)', line)
        if match and current is not None:
            tokens = [int(token) for token in match.group(2).split(',')]
            length = int(match.group(3))
            if current[0] == length:
                result.setdefault((length, tokens[-1]), []).append(current[1])
            current = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True, help='run directory with serial logs and batch hash text')
    parser.add_argument('--batch-hashes', type=Path, default=None)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    batch_path = args.batch_hashes or args.run / 'batch-qsa-state-hashes.txt'
    serial = {}
    for slot in (0, 1):
        for key, values in serial_prefixes(args.run / f'serial-slot-{slot}.log').items():
            serial.setdefault(key, []).extend((slot, value) for value in values)

    rows = []
    for line in batch_path.read_text().splitlines():
        fields = dict(item.split('=', 1) for item in line.split() if '=' in item)
        if 'position' not in fields or 'hashes' not in fields:
            continue
        key = (int(fields['state_length']), int(fields['token']))
        candidates = serial.get(key, [])
        hash_match = re.search(r' hashes=(.*)$', line)
        batch_hashes = hash_match.group(1).split() if hash_match else []
        comparisons = []
        for serial_slot, hashes in candidates:
            differences = [i for i, (a, b) in enumerate(zip(batch_hashes, hashes)) if a != b]
            comparisons.append({
                'serial_slot': serial_slot,
                'exact': not differences and len(batch_hashes) == len(hashes),
                'first_differing_qsa_ordinal': differences[0] if differences else None,
                'first_differing_model_layer': (differences[0] + 1) * 4 - 1 if differences else None,
                'differing_layers': len(differences),
                'compared_layers': min(len(batch_hashes), len(hashes)),
            })
        rows.append({
            'position': int(fields['position']), 'state_length': key[0], 'token': key[1],
            'batch_slot': int(fields['slot']), 'batch_row': int(fields['row']),
            'serial_candidates': comparisons,
            'status': 'paired' if candidates else 'no-exact-length-token-control',
        })
    result = {'schema': 1, 'scope': 'diagnostic hash comparison; not a correctness or performance gate',
              'batch_hash_file': str(batch_path), 'rows': rows}
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
