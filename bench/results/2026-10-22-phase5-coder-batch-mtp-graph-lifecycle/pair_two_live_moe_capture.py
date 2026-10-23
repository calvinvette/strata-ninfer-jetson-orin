#!/usr/bin/env python3
"""Extract one serial/batch MoE row pair by exact activation and slot."""
import argparse
import json
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--capture', type=Path, required=True,
                    help='directory written by capture_two_live_layer4.py')
parser.add_argument('--serial-prompt', type=int, choices=(0, 1), required=True)
parser.add_argument('--layer', type=int, required=True)
parser.add_argument('--position', type=int, required=True)
parser.add_argument('--slot', type=int, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
capture, output = args.capture, args.output
output.mkdir(parents=True, exist_ok=False)
serial_stem = f'serial-prompt{args.serial_prompt}'

def read_jsonl(path):
    lines = path.read_text().splitlines()
    if not lines:
        raise ValueError(f'{path}: empty capture')
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:]]

serial_header, serial_rows = read_jsonl(capture / f'{serial_stem}.owners.jsonl')
batch_header, batch_rows = read_jsonl(capture / 'batch.owners.jsonl')
serial_matches = [r for r in serial_rows if r.get('layer') == args.layer and r.get('position') == args.position]
if len(serial_matches) != 1 or not serial_matches[0].get('activation_valid'):
    raise ValueError(f'expected one valid serial owner row, got {len(serial_matches)}')
serial_owner = serial_matches[0]
activation = struct.pack(f'<{len(serial_owner["activation"])}f', *serial_owner['activation'])
batch_matches = [r for r in batch_rows if r.get('layer') == args.layer
                 and r.get('position') == args.position
                 and r.get('token_id') == serial_owner['token_id']
                 and r.get('activation_valid')
                 and struct.pack(f'<{len(r["activation"])}f', *r['activation']) == activation]
if len(batch_matches) != 1:
    raise ValueError(f'exact activation did not select one batch owner row: {len(batch_matches)}')
batch_owner = batch_matches[0]
token = serial_owner['token_id']
(output / 'serial.moe-owners.jsonl').write_text(
    json.dumps(serial_header, separators=(',', ':')) + '\n' +
    json.dumps(serial_owner, separators=(',', ':')) + '\n')
(output / 'batch.moe-owners.jsonl').write_text(
    json.dumps(batch_header, separators=(',', ':')) + '\n' +
    json.dumps(batch_owner, separators=(',', ':')) + '\n')

route_header = None
route_pair = []
for path, slot in ((capture / f'{serial_stem}.routes.jsonl', None),
                   (capture / 'batch.routes.jsonl', args.slot)):
    header, rows = read_jsonl(path)
    route_header = route_header or header
    selected = [r for r in rows if r.get('layer') == args.layer and r.get('position') == args.position
                and r.get('token_id') == token
                and (slot is None or r.get('slot') == slot)]
    if len(selected) != 1:
        raise ValueError(f'{path}: expected one route record, got {len(selected)}')
    route_pair.extend(selected)
for label, owner, route in (('serial', serial_owner, route_pair[0]),
                            ('batch', batch_owner, route_pair[1])):
    if owner['ids'] != route['ids']:
        raise ValueError(f'{label}: owner and verifier route IDs disagree for the selected activation/slot; '
                         'the row pair is unsupported')
(output / 'moe-routes.jsonl').write_text(
    json.dumps(route_header, separators=(',', ':')) + '\n' +
    '\n'.join(json.dumps(r, separators=(',', ':')) for r in route_pair) + '\n')

header = struct.Struct('<8sIIIIQqii')
for suffix, magic, arrays, name in (
    ('parts.stmparts', b'STMPART2', 1, 'moe-parts.stmparts'),
    ('output.stmoe', b'MOEOUT02', 2, 'moe-output.stmoe'),
):
    selected_records = []
    for path, slot in ((capture / f'{serial_stem}.{suffix}', -1),
                       (capture / f'batch.{suffix}', args.slot)):
        data, at = path.read_bytes(), 0
        selected = []
        while at < len(data):
            if len(data) - at < header.size:
                raise ValueError(f'{path}: truncated header at {at}')
            fields = header.unpack_from(data, at)
            got_magic, version, layer, count, reserved, width, position, row_slot, row_token = fields
            size = header.size + count * width * arrays * 4
            if got_magic != magic or version != 2 or reserved:
                raise ValueError(f'{path}: malformed record at {at}')
            if (layer, position, row_slot, row_token) == (args.layer, args.position, slot, token):
                selected.append(data[at:at + size])
            at += size
        if len(selected) != 1:
            raise ValueError(f'{path}: expected one selected record, got {len(selected)}')
        selected_records.extend(selected)
    (output / name).write_bytes(b''.join(selected_records))

print(json.dumps({'layer': args.layer, 'position': args.position, 'token': token,
                  'slot': args.slot, 'activation_bytes': len(activation)}))
