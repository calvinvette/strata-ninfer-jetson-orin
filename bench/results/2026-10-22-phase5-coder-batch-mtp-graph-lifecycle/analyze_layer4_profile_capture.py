#!/usr/bin/env python3
"""Join the expert-11-first two-live capture by route slot and committed state."""
import argparse
from array import array
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct

STATE_HEADER = struct.Struct('<8sIiqQQii')
ROW_HEADER = struct.Struct('<8sIIIIQqii')
LAYERS = (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21,
          22, 24, 25, 26, 28, 29, 30, 32, 33, 34, 36, 37, 38, 40, 41,
          42, 44, 45, 46)


def json_rows(path):
    lines = path.read_text().splitlines()
    if not lines:
        raise ValueError(f'{path}: empty JSONL capture')
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:]]


def read_states(path):
    data, at = path.read_bytes(), 0
    records = {}
    while at < len(data):
        if len(data) - at < STATE_HEADER.size:
            raise ValueError(f'{path}: truncated state header')
        magic, version, layer, position, recurrent, total, token, slot = STATE_HEADER.unpack_from(data, at)
        at += STATE_HEADER.size
        size = total * 4
        if magic != b'STGCMT1\0' or version != 1 or total < recurrent or len(data) - at < size:
            raise ValueError(f'{path}: malformed GDN state record')
        key = (slot, position, layer)
        if key in records:
            raise ValueError(f'{path}: duplicate state key {key}')
        records[key] = {'bytes': data[at:at + size], 'recurrent': recurrent, 'token': token}
        at += size
    return records


def read_rows(path, magic, arrays):
    data, at = path.read_bytes(), 0
    records = {}
    while at < len(data):
        if len(data) - at < ROW_HEADER.size:
            raise ValueError(f'{path}: truncated row header')
        fields = ROW_HEADER.unpack_from(data, at)
        got_magic, version, layer, count, reserved, width, position, slot, token = fields
        size = ROW_HEADER.size + count * width * arrays * 4
        if got_magic != magic or version != 2 or reserved != 0 or len(data) - at < size:
            raise ValueError(f'{path}: malformed row record')
        records[(slot, position, layer, token)] = data[at + ROW_HEADER.size:at + size]
        at += size
    return records


def vector_delta(reference, candidate):
    a, b = array('f'), array('f')
    a.frombytes(reference)
    b.frombytes(candidate)
    if len(a) != len(b):
        raise ValueError('state vector sizes differ')
    changed = sum(x != y for x, y in zip(a, b))
    delta_sq = sum((x - y) ** 2 for x, y in zip(a, b))
    reference_sq = sum(x * x for x in a)
    return {'values': len(a), 'different_values': changed,
            'relative_l2': (delta_sq / reference_sq) ** 0.5 if reference_sq else None}


def route_for(rows, prompt, position):
    selected = [row for row in rows if row.get('layer') == 4 and row.get('position') == position]
    if len(selected) != 1:
        raise ValueError(f'prompt {prompt} at {position}: expected one serial layer-4 route')
    return selected[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--supervisor', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    capture = args.capture.resolve()
    profile_hash = hashlib.sha256(args.profile.read_bytes()).hexdigest()
    if profile_hash != '8a590044b65ae494e3462067cd76878f3b71ca23519c182ac4660d88c6d9f114':
        raise ValueError(f'unexpected expert profile SHA256: {profile_hash}')
    run = json.loads((capture / 'result.json').read_text())
    supervision = json.loads((args.supervisor / 'result.json').read_text())
    if supervision.get('status') != 'pass' or supervision.get('returncode') != 0:
        raise ValueError('supervisor did not pass')
    if supervision['minimum_available_bytes'] < supervision['floor_bytes']:
        raise ValueError('physical-memory floor was breached')
    event_max = defaultdict(int)
    samples = 0
    for line in (args.supervisor / 'memory.jsonl').read_text().splitlines():
        sample = json.loads(line)
        samples += 1
        for cgroup in sample.get('cgroups', []):
            for name, value in cgroup.get('memory_events', {}).items():
                event_max[name] = max(event_max[name], int(value))
    if samples == 0 or any(event_max[name] != 0 for name in ('low', 'high', 'max', 'oom', 'oom_kill')):
        raise ValueError(f'missing memory samples or non-zero cgroup events: {dict(event_max)}')
    if run['token_match'] != {'slot-0': True, 'slot-1': True}:
        raise ValueError('serial and batch token streams do not match')
    if run['moe_positions'] != [68, 71] or run['state_positions'] != [68, 71]:
        raise ValueError('capture does not contain both requested positions')

    _, batch_routes = json_rows(capture / 'batch.routes.jsonl')
    route_map = {}
    route_weights_exact = {}
    missing_route_slots = []
    for prompt in (0, 1):
        _, serial_routes = json_rows(capture / f'serial-prompt{prompt}.routes.jsonl')
        for position in (68, 71):
            serial = route_for(serial_routes, prompt, position)
            matches = [row for row in batch_routes if row.get('layer') == 4 and
                       row.get('position') == position and row.get('token_id') == serial['token_id'] and
                       row.get('ids') == serial['ids']]
            if len(matches) != 1:
                raise ValueError(f'prompt {prompt} at {position}: route pair count {len(matches)}')
            route_weights_exact[(prompt, position)] = matches[0].get('weights') == serial['weights']
            if position == 68 and not route_weights_exact[(prompt, position)]:
                raise ValueError(f'prompt {prompt} at {position}: expected exact prompt-boundary route weights')
            slot = matches[0].get('slot')
            if slot is None:
                missing_route_slots.append((prompt, position))
            else:
                key = (prompt, position)
                if key in route_map and route_map[key] != slot:
                    raise ValueError(f'prompt {prompt}: physical slot changed across selected positions')
                route_map[key] = slot
    if route_map.get((0, 71)) != 0 or route_map.get((1, 71)) != 1:
        raise ValueError(f'unexpected explicit position-71 slot mapping: {route_map}')
    if missing_route_slots != [(0, 68)]:
        raise ValueError(f'unexpected missing route-slot metadata: {missing_route_slots}')
    # At position 68, prompt 1 is explicitly slot 1; the only remaining row is
    # prompt 0 / slot 0. Position 71 independently confirms that mapping.
    route_map[(0, 68)] = 0

    state = {
        prompt: read_states(capture / f'serial-prompt{prompt}.stgcmt')
        for prompt in (0, 1)
    }
    batch_state = read_states(capture / 'batch.stgcmt')
    state_report = {}
    for prompt in (0, 1):
        slot = route_map[(prompt, 71)]
        points = {}
        for position in (68, 71):
            comparisons = []
            for layer in LAYERS:
                serial_key = (0, position, layer)
                batch_key = (slot, position, layer)
                if serial_key not in state[prompt] or batch_key not in batch_state:
                    raise ValueError(f'missing state record for prompt {prompt}, slot {slot}, {position}/{layer}')
                a = state[prompt][serial_key]['bytes']
                b = batch_state[batch_key]['bytes']
                if a != b:
                    comparisons.append((layer, a, b))
            first = comparisons[0] if comparisons else None
            points[str(position)] = {
                'gdn_layers': len(LAYERS), 'exact_layers': len(LAYERS) - len(comparisons),
                'different_layers': len(comparisons),
                'first_differing_layer': first[0] if first else None,
                'first_difference': vector_delta(first[1], first[2]) if first else None,
                'layer4_difference': next((vector_delta(a, b) for layer, a, b in comparisons
                                           if layer == 4), None),
            }
        state_report[f'prompt{prompt}_slot{slot}'] = points

    owner_pairs = {}
    _, batch_owner_rows = json_rows(capture / 'batch.owners.jsonl')
    for prompt in (0, 1):
        _, serial_owner_rows = json_rows(capture / f'serial-prompt{prompt}.owners.jsonl')
        serial_owner = [x for x in serial_owner_rows if x.get('layer') == 4 and x.get('position') == 71]
        if len(serial_owner) != 1:
            raise ValueError(f'expected one prompt-{prompt} serial owner row at position 71')
        serial_owner = serial_owner[0]
        batch_owner = [x for x in batch_owner_rows if x.get('layer') == 4 and x.get('position') == 71 and
                       x.get('token_id') == serial_owner['token_id'] and x.get('ids') == serial_owner['ids']]
        if len(batch_owner) != 1:
            raise ValueError(f'expected one prompt-{prompt} batch owner row at position 71')
        owner_pairs[prompt] = (serial_owner, batch_owner[0])
    serial_owner, batch_owner = owner_pairs[0]
    if serial_owner['route_kind'] != batch_owner['route_kind']:
        raise ValueError('prompt-0 owner codes differ despite exact activation/routes')
    activation_exact = (struct.pack(f'<{len(serial_owner["activation"])}f', *serial_owner['activation']) ==
                        struct.pack(f'<{len(batch_owner["activation"])}f', *batch_owner['activation']))
    if not activation_exact:
        raise ValueError('prompt-0 activation differs')
    parts = read_rows(capture / 'serial-prompt0.parts.stmparts', b'STMPART2', 1)
    batch_parts = read_rows(capture / 'batch.parts.stmparts', b'STMPART2', 1)
    serial_output = read_rows(capture / 'serial-prompt0.output.stmoe', b'MOEOUT02', 2)
    batch_output = read_rows(capture / 'batch.output.stmoe', b'MOEOUT02', 2)
    part_key, output_key = (-1, 71, 4, 1156), (-1, 71, 4, 1156)
    batch_part_key, batch_output_key = (0, 71, 4, 1156), (0, 71, 4, 1156)
    if parts.get(part_key) is None or batch_parts.get(batch_part_key) is None or \
            serial_output.get(output_key) is None or batch_output.get(batch_output_key) is None:
        raise ValueError('prompt-0 selected parts/output capture is incomplete')
    if parts[part_key] != batch_parts[batch_part_key] or serial_output[output_key] != batch_output[batch_output_key]:
        raise ValueError('prompt-0 parts or output differ')

    def activation_summary(prompt):
        serial, batch = owner_pairs[prompt]
        if not serial.get('activation_valid') or not batch.get('activation_valid'):
            return {'available': False}
        serial_bytes = struct.pack(f'<{len(serial["activation"])}f', *serial['activation'])
        batch_bytes = struct.pack(f'<{len(batch["activation"])}f', *batch['activation'])
        return {'available': True, 'exact': serial_bytes == batch_bytes,
                'delta': None if serial_bytes == batch_bytes else vector_delta(serial_bytes, batch_bytes)}

    result = {
        'scope': 'one current-source two-live target-only diagnostic with expert-11-first profile',
        'position_pair': [68, 71], 'model_layer': 4,
        'profile_sha256': profile_hash,
        'binary_sha256': hashlib.sha256(Path('build/integration/candidate/strata').read_bytes()).hexdigest(),
        'minimum_available_bytes': supervision['minimum_available_bytes'],
        'minimum_admission_available_bytes': supervision['minimum_admission_available_bytes'],
        'memory_samples': samples, 'maximum_cgroup_events': dict(event_max),
        'token_streams_match_serial_for_both_requests': True,
        'route_join': {
            'mapping': {'prompt0': 0, 'prompt1': 1},
            'position68_prompt0_slot_inferred_by_complement': True,
            'position71_slots_explicit': True,
            'route_ids_exact_at_both_positions': True,
            'weights_exact': {f'prompt{p}_position{pos}': exact
                              for (p, pos), exact in route_weights_exact.items()},
        },
        'committed_state': state_report,
        'layer4_position71_prompt0': {
            'activation_exact': True, 'expert_ids_and_weights_exact': True,
            'owner_codes': serial_owner['route_kind'],
            'expert_parts_exact': True, 'shared_and_combined_outputs_exact': True,
        },
        'layer4_position71_prompt1': {
            'activation': activation_summary(1),
            'route_ids_exact': True,
            'route_weights_exact': route_weights_exact[(1, 71)],
            'owner_codes_equal': owner_pairs[1][0]['route_kind'] == owner_pairs[1][1]['route_kind'],
            'expert_output_comparison': 'not attributed because verifier activation differs',
        },
        'interpretation_limit': 'prompt1 layer-4 activation and route weights differ, so its expert output delta is not attributable. Prompt0 layer-4 input, routes, expert parts and combined output are exact, but later committed state first differs at layer 6. This does not locate all upstream numerical differences or qualify multi-live serving.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
