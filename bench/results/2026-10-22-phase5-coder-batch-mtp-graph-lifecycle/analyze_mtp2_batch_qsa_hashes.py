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
            hashes = re.findall(r'qsa=(\d+) layer=(\d+) hash=([0-9a-f]+) idx=([0-9a-f]+) kv=([0-9a-f]+)', match.group(2))
            current = (int(match.group(1)), {
                'aggregate': [row[2] for row in hashes],
                'index': [row[3] for row in hashes],
                'kv': [row[4] for row in hashes],
            })
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
    for path in sorted(args.run.glob('serial-slot-*.log')):
        slot = int(path.stem.rsplit('-', 1)[1])
        for key, values in serial_prefixes(path).items():
            serial.setdefault(key, []).extend((slot, value) for value in values)

    rows = []
    batch_groups = {}
    for line in batch_path.read_text().splitlines():
        fields = dict(item.split('=', 1) for item in line.split() if '=' in item)
        if 'position' not in fields or 'hashes' not in fields:
            continue
        key = (int(fields['state_length']), int(fields['token']))
        candidates = serial.get(key, [])
        def values(name):
            stop = {'hashes': r'(?= idx_hashes=)', 'idx_hashes': r'(?= kv_hashes=)',
                    'kv_hashes': r'$'}[name]
            match = re.search(rf' {name}=(.*?){stop}', line)
            return match.group(1).split() if match else []
        batch_hashes = values('hashes')
        batch_index_hashes = values('idx_hashes')
        batch_kv_hashes = values('kv_hashes')
        key = (int(fields['state_length']), int(fields['token']))
        batch_record = {
            'position': int(fields['position']), 'state_length': key[0], 'token': key[1],
            'batch_slot': int(fields['slot']), 'batch_row': int(fields['row']),
            'aggregate': batch_hashes, 'index': batch_index_hashes, 'kv': batch_kv_hashes,
        }
        batch_groups.setdefault(key, []).append(batch_record)
        comparisons = []
        for serial_slot, hashes in candidates:
            differences = [i for i, (a, b) in enumerate(zip(batch_hashes, hashes['aggregate'])) if a != b]
            index_differences = [i for i, (a, b) in enumerate(zip(batch_index_hashes, hashes['index'])) if a != b]
            kv_differences = [i for i, (a, b) in enumerate(zip(batch_kv_hashes, hashes['kv'])) if a != b]
            comparisons.append({
                'serial_slot': serial_slot,
                'exact': not differences and len(batch_hashes) == len(hashes['aggregate']),
                'first_differing_qsa_ordinal': differences[0] if differences else None,
                'first_differing_model_layer': (differences[0] + 1) * 4 - 1 if differences else None,
                'differing_layers': len(differences),
                'index_first_differing_qsa_ordinal': index_differences[0] if index_differences else None,
                'index_differing_layers': len(index_differences),
                'kv_first_differing_qsa_ordinal': kv_differences[0] if kv_differences else None,
                'kv_differing_layers': len(kv_differences),
                'compared_layers': min(len(batch_hashes), len(hashes['aggregate'])),
            })
        rows.append({
            **{k: batch_record[k] for k in ('position', 'state_length', 'token', 'batch_slot', 'batch_row')},
            'aggregate': batch_hashes, 'index': batch_index_hashes, 'kv': batch_kv_hashes,
            'serial_candidates': comparisons,
            'status': 'paired' if candidates else 'no-exact-length-token-control',
        })
    for row in rows:
        peers = []
        for other in batch_groups[(row['state_length'], row['token'])]:
            if (other['batch_slot'], other['batch_row']) == (row['batch_slot'], row['batch_row']):
                continue
            differences = [i for i, (a, b) in enumerate(zip(row['aggregate'], other['aggregate'])) if a != b]
            index_differences = [i for i, (a, b) in enumerate(zip(row['index'], other['index'])) if a != b]
            kv_differences = [i for i, (a, b) in enumerate(zip(row['kv'], other['kv'])) if a != b]
            peers.append({
                'batch_slot': other['batch_slot'], 'batch_row': other['batch_row'],
                'exact': not differences and len(row['aggregate']) == len(other['aggregate']),
                'aggregate_differing_layers': len(differences),
                'index_differing_layers': len(index_differences),
                'kv_differing_layers': len(kv_differences),
                'first_differing_qsa_ordinal': differences[0] if differences else None,
            })
        row['batch_peers'] = peers
        del row['aggregate'], row['index'], row['kv']
    result = {'schema': 2, 'scope': 'diagnostic hash comparison; not a correctness or performance gate',
              'batch_hash_file': str(batch_path), 'rows': rows}
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
