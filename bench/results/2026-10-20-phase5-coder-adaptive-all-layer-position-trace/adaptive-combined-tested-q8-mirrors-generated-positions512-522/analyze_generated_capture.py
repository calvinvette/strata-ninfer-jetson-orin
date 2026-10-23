#!/usr/bin/env python3
"""Compactly compare generated-position MoE inputs and layer-32 raw state."""
import json
import re
import struct
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER = struct.Struct('<8sIiqQQii')
PREFIX = re.compile(r'ACCEPTED_PREFIX position=(\d+).*?tokens=([0-9,]+)')

def state_rows(path):
    raw = path.read_bytes()
    rows = defaultdict(list)
    offset = 0
    while offset < len(raw):
        magic, version, layer, pos, recurrent, total, token, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != 32 or reserved or total < recurrent:
            raise ValueError('invalid layer-32 state record')
        size = total * 4
        rows[pos].append({'token': token, 'pre': (offset, offset + size),
                          'post': (offset + size, offset + 2 * size), 'recurrent': recurrent})
        offset += 2 * size
    return raw, rows

def main():
    out = {'scope': 'all-layer verifier inputs and raw layer-32 GDN states, positions 512-522', 'arms': {}}
    for arm in ('delayed-control', 'adaptive-cap8'):
        run = HERE / arm / 'result'
        records = [json.loads(line) for line in (run / 'all-layer-selected-positions.jsonl').read_text().splitlines()][1:]
        by_pos = defaultdict(list)
        for row in records:
            by_pos[row['position']].append(row)
        activation = {}
        for pos, rows in sorted(by_pos.items()):
            if len(rows) != 144:
                raise ValueError(f'{arm}/{pos}: expected 3x48 rows, found {len(rows)}')
            blocks = [rows[i:i+48] for i in (0, 48, 96)]
            transitions = []
            for a, b in ((blocks[0], blocks[1]), (blocks[1], blocks[2])):
                transitions.append({
                    'activation_difference_layers': [x['layer'] for x,y in zip(a,b) if x['activation'] != y['activation']],
                    'expert_id_difference_layers': [x['layer'] for x,y in zip(a,b) if x['ids'] != y['ids']],
                    'owner_difference_layers': [x['layer'] for x,y in zip(a,b) if x['route_kind'] != y['route_kind']],
                })
            activation[str(pos)] = transitions
        raw, states = state_rows(run / 'gdn-state.bin')
        state_results = {}
        for pos, rows in sorted(states.items()):
            if len(rows) != 3:
                raise ValueError(f'{arm}/{pos}: expected three raw state rows, found {len(rows)}')
            transitions=[]
            for a,b in ((rows[0],rows[1]),(rows[1],rows[2])):
                transitions.append({
                    'token_ids_equal': a['token']==b['token'],
                    'pre_state_equal': memoryview(raw)[slice(*a['pre'])] == memoryview(raw)[slice(*b['pre'])],
                    'post_state_equal': memoryview(raw)[slice(*a['post'])] == memoryview(raw)[slice(*b['post'])],
                })
            state_results[str(pos)] = transitions
        out['arms'][arm] = {'activation_transitions': activation, 'layer32_state_transitions': state_results}
    (HERE / 'generated-position-analysis.json').write_text(json.dumps(out, indent=2)+'\n')
    for arm,data in out['arms'].items():
        print(arm)
        for pos,transitions in data['activation_transitions'].items():
            print(pos,[(t['activation_difference_layers'][:1],len(t['activation_difference_layers']),t['expert_id_difference_layers'][:1]) for t in transitions],
                  'state',data['layer32_state_transitions'].get(pos))

if __name__ == '__main__': main()
