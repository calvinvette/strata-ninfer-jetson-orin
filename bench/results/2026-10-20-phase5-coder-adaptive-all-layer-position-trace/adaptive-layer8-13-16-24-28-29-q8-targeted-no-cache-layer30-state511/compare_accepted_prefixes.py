#!/usr/bin/env python3
"""Compare accepted-prefix hashes across three repeated same-service requests."""
from collections import defaultdict
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LINE = re.compile(r'ACCEPTED_PREFIX position=(\d+).*?tokens=(\d+) state=\{STATE_HASH (.*?)\}')
GDN_LINE = re.compile(r'STATE_HASH_GDN ((?:[0-9a-f]{16}\s*)+)')


def read(path):
    positions = defaultdict(list)
    gdn_positions = defaultdict(list)
    pending_gdn = None
    for line in path.read_text(errors='replace').splitlines():
        gdn_match = GDN_LINE.search(line)
        if gdn_match:
            pending_gdn = gdn_match.group(1).split()
        match = LINE.search(line)
        if not match:
            continue
        position, token = map(int, match.group(1, 2))
        state = dict(field.split('=', 1) for field in match.group(3).split() if '=' in field)
        positions[position].append({'token_id': token, 'state': state})
        if pending_gdn is None:
            raise ValueError(f'{path}: accepted prefix at {position} is missing per-GDN hashes')
        gdn_positions[position].append(pending_gdn)
        pending_gdn = None
    if not positions or any(len(rows) != 3 for rows in positions.values()):
        raise ValueError(f'{path}: expected three same-service records at each accepted position')
    if set(positions) != set(gdn_positions) or any(len(rows) != 3 for rows in gdn_positions.values()):
        raise ValueError(f'{path}: accepted-prefix and per-GDN hash record counts differ')
    return positions, gdn_positions


def compare(left, right):
    fields = sorted(set(left['state']) | set(right['state']))
    changed = [key for key in fields if left['state'].get(key) != right['state'].get(key)]
    return {'token_ids_equal': left['token_id'] == right['token_id'],
            'changed_state_fields': changed,
            'equal': not changed and left['token_id'] == right['token_id']}


def main():
    output = {'scope': 'same-service accepted-prefix fingerprints with prompt cache disabled', 'arms': {}}
    for arm in ('delayed-control', 'adaptive-cap8'):
        positions, gdn_positions = read(ROOT / arm / 'result' / 'service.log')
        rows = {}
        for position, requests in sorted(positions.items()):
            transitions = [compare(requests[i], requests[i + 1]) for i in (0, 1)]
            for index, transition in enumerate(transitions):
                left, right = gdn_positions[position][index:index + 2]
                if len(left) != len(right):
                    raise ValueError(f'{arm} position {position}: GDN hash vector lengths differ')
                transition['changed_gdn_ordinals'] = [ordinal for ordinal, (a, b) in enumerate(zip(left, right))
                                                      if a != b]
            rows[str(position)] = {'initial_to_intermediate': transitions[0],
                                   'intermediate_to_recovery': transitions[1]}
        output['arms'][arm] = {
            'positions': rows,
            'initial_to_intermediate_first_difference': next(
                (int(position) for position, row in rows.items() if not row['initial_to_intermediate']['equal']), None),
            'initial_to_recovery_shared_state_equal_at_all_positions': all(
                requests[0]['state'] == requests[2]['state'] and requests[0]['token_id'] == requests[2]['token_id']
                for requests in positions.values()),
        }
    path = ROOT / 'accepted-prefix-analysis.json'
    path.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({arm: {'initial_to_intermediate_first_difference': data['initial_to_intermediate_first_difference'],
                            'initial_to_recovery_shared_state_equal_at_all_positions': data['initial_to_recovery_shared_state_equal_at_all_positions']}
                      for arm, data in output['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
