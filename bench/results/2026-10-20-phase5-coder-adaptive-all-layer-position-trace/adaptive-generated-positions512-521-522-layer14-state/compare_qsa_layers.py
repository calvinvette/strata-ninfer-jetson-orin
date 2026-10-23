#!/usr/bin/env python3
"""Compare accepted-prefix per-QSA hashes at selected positions."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

PREFIX = re.compile(r'ACCEPTED_PREFIX position=(\d+)')
QSA = re.compile(r'STATE_HASH_QSA_LAYERS L=(\d+)((?: qsa=\d+ layer=\d+ hash=[0-9a-f]+)+)')
ENTRY = re.compile(r'qsa=(\d+) layer=(\d+) hash=([0-9a-f]+)')
START_POSITION = 511


def read_requests(path, positions, request_count):
    requests = []
    current = None
    pending = None
    for line in path.read_text(errors='replace').splitlines():
        match = QSA.search(line)
        if match:
            pending = {int(qsa): {'layer': int(layer), 'hash': digest}
                       for qsa, layer, digest in ENTRY.findall(match.group(2))}
            continue
        match = PREFIX.search(line)
        if not match:
            continue
        position = int(match.group(1))
        if position == START_POSITION:
            if current is not None:
                requests.append(current)
            current = {}
        if current is None:
            continue
        if pending is not None and position in positions:
            if position in current:
                raise ValueError(f'{path}: duplicate per-QSA hashes for position {position} in one request')
            current[position] = pending
        pending = None
    if current is not None:
        requests.append(current)
    if len(requests) != request_count:
        raise ValueError(f'{path}: expected {request_count} request blocks, got {len(requests)}')
    for request_index, request in enumerate(requests):
        missing = positions - set(request)
        if missing:
            raise ValueError(f'{path}: request {request_index} missing QSA position(s) {sorted(missing)}')
    return requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    campaign = json.loads((args.run_dir / 'campaign.json').read_text())
    if campaign.get('status') != 'pass':
        raise ValueError('paired campaign did not pass')
    names = [row['name'] for row in campaign['runs'][0]['analysis']['requests']]
    positions = set(campaign['gdn_state_positions'])
    if not positions:
        raise ValueError('campaign has no selected raw-state positions')
    comparisons = [(i, i + 1, f'{names[i]}_to_{names[i + 1]}') for i in range(len(names) - 1)]
    output = {'scope': 'per-QSA accepted-state hashes at selected accepted-prefix positions',
              'positions': sorted(positions), 'requests': names, 'arms': {}}
    for arm in ('adaptive-cap8', 'delayed-control'):
        rows = read_requests(args.run_dir / arm / 'result' / 'service.log', positions, len(names))
        arm_result = {}
        for position in sorted(positions):
            transitions = {}
            for left, right, name in comparisons:
                a, b = rows[left][position], rows[right][position]
                keys = sorted(set(a) | set(b))
                changed = []
                for qsa in keys:
                    if qsa not in a or qsa not in b:
                        changed.append({'qsa': qsa, 'reason': 'missing hash in one request'})
                    elif a[qsa] != b[qsa]:
                        changed.append({'qsa': qsa, 'layer': a[qsa]['layer'],
                                        'left_hash': a[qsa]['hash'], 'right_hash': b[qsa]['hash']})
                transitions[name] = {'different_qsa_count': len(changed), 'differences': changed}
            arm_result[str(position)] = transitions
        output['arms'][arm] = arm_result
    (args.run_dir / 'qsa-state-analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({arm: {pos: {name: row['different_qsa_count']
                                 for name, row in transitions.items()}
                              for pos, transitions in data.items()}
                      for arm, data in output['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
