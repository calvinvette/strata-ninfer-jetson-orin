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
    absolute_l2 = delta_sq ** 0.5
    return {'values': len(a), 'different_values': changed,
            'absolute_l2': absolute_l2,
            'max_abs': max((abs(x - y) for x, y in zip(a, b)), default=0.0),
            'relative_l2': absolute_l2 / (reference_sq ** 0.5) if reference_sq else None}


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
    parser.add_argument('--q8-1-selector', choices=('none', 'all'), default='none')
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
    explicit_route_map = {}
    route_weights_exact = {}
    route_pairs = {}
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
            route_pairs[(prompt, position)] = (serial, matches[0])
            if position == 68 and not route_weights_exact[(prompt, position)]:
                raise ValueError(f'prompt {prompt} at {position}: expected exact prompt-boundary route weights')
            slot = matches[0].get('slot')
            if slot is None:
                missing_route_slots.append((prompt, position))
            else:
                route_map[(prompt, position)] = slot
                explicit_route_map[(prompt, position)] = slot
    if any((prompt, 71) not in explicit_route_map for prompt in (0, 1)):
        raise ValueError(f'position-71 route slots are not explicit: {explicit_route_map}')
    if set(explicit_route_map[(prompt, 71)] for prompt in (0, 1)) != {0, 1}:
        raise ValueError(f'position-71 routes do not identify both physical slots: {explicit_route_map}')
    missing68 = [prompt for prompt in (0, 1) if (prompt, 68) in missing_route_slots]
    if len(missing68) > 1:
        raise ValueError(f'multiple position-68 rows omit slot: {missing_route_slots}')
    if missing68:
        prompt = missing68[0]
        other = 1 - prompt
        if (other, 68) not in route_map:
            raise ValueError(f'cannot infer missing position-68 slot: {route_map}')
        route_map[(prompt, 68)] = 1 - route_map[(other, 68)]
    for position in (68, 71):
        if set(route_map.get((prompt, position)) for prompt in (0, 1)) != {0, 1}:
            raise ValueError(f'position {position} does not identify both physical slots: {route_map}')
    for prompt in (0, 1):
        if route_map[(prompt, 68)] != route_map[(prompt, 71)]:
            raise ValueError(f'prompt {prompt}: physical slot assignment changes across positions')

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
        for position in (68, 71):
            serial_owner = [x for x in serial_owner_rows if x.get('layer') == 4 and x.get('position') == position]
            if len(serial_owner) != 1:
                raise ValueError(f'expected one prompt-{prompt} serial owner row at {position}')
            serial_owner = serial_owner[0]
            batch_owner = [x for x in batch_owner_rows if x.get('layer') == 4 and x.get('position') == position and
                           x.get('token_id') == serial_owner['token_id'] and x.get('ids') == serial_owner['ids']]
            if len(batch_owner) != 1:
                raise ValueError(f'expected one prompt-{prompt} batch owner row at {position}')
            owner_pairs[(prompt, position)] = (serial_owner, batch_owner[0])

    def activation_summary(prompt, position):
        serial, batch = owner_pairs[(prompt, position)]
        if not serial.get('activation_valid') or not batch.get('activation_valid'):
            return {'available': False}
        serial_bytes = struct.pack(f'<{len(serial["activation"])}f', *serial['activation'])
        batch_bytes = struct.pack(f'<{len(batch["activation"])}f', *batch['activation'])
        return {'available': True, 'exact': serial_bytes == batch_bytes,
                'delta': None if serial_bytes == batch_bytes else vector_delta(serial_bytes, batch_bytes)}

    moe_rows = {}
    for prompt in (0, 1):
        for position in (68, 71):
            serial_route, batch_route = route_pairs[(prompt, position)]
            serial_owner, batch_owner = owner_pairs[(prompt, position)]
            activation = activation_summary(prompt, position)
            qualified = (activation.get('exact', False) and
                         route_weights_exact[(prompt, position)] and
                         serial_route['ids'] == batch_route['ids'])
            details = {'activation': activation,
                       'route_ids_exact': serial_route['ids'] == batch_route['ids'],
                       'route_weights_exact': route_weights_exact[(prompt, position)],
                       'owner_codes_equal': serial_owner['route_kind'] == batch_owner['route_kind'],
                       'owner_changes': [{'rank': rank, 'expert': serial_route['ids'][rank],
                                          'serial': serial_owner['route_kind'][rank],
                                          'batch': batch_owner['route_kind'][rank]}
                                         for rank in range(10)
                                         if serial_owner['route_kind'][rank] != batch_owner['route_kind'][rank]],
                       'qualified_same_input_output_comparison': qualified}
            if qualified:
                serial_parts = read_rows(capture / f'serial-prompt{prompt}.parts.stmparts', b'STMPART2', 1)
                batch_parts = read_rows(capture / 'batch.parts.stmparts', b'STMPART2', 1)
                serial_output = read_rows(capture / f'serial-prompt{prompt}.output.stmoe', b'MOEOUT02', 2)
                batch_output = read_rows(capture / 'batch.output.stmoe', b'MOEOUT02', 2)
                token = serial_route['token_id']
                part_key = (-1, position, 4, token)
                batch_key = (route_map[(prompt, position)], position, 4, token)
                if part_key not in serial_parts or batch_key not in batch_parts or \
                        part_key not in serial_output or batch_key not in batch_output:
                    details['output_comparison'] = 'qualified inputs, but slot-tagged batch parts/output are unavailable'
                    moe_rows[f'prompt{prompt}_position{position}'] = details
                    continue
                serial_blob, batch_blob = serial_parts[part_key], batch_parts[batch_key]
                changed_ranks = [rank for rank in range(10)
                                 if serial_blob[rank * 2560 * 4:(rank + 1) * 2560 * 4] !=
                                 batch_blob[rank * 2560 * 4:(rank + 1) * 2560 * 4]]
                serial_out, batch_out = serial_output[part_key], batch_output[batch_key]
                details['expert_parts_exact'] = not changed_ranks
                details['changed_expert_parts'] = [{'rank': rank, 'expert': serial_route['ids'][rank]}
                                                   for rank in changed_ranks]
                details['changed_expert_part_deltas'] = [
                    {'rank': rank, 'expert': serial_route['ids'][rank],
                     'delta': vector_delta(
                         serial_blob[rank * 2560 * 4:(rank + 1) * 2560 * 4],
                         batch_blob[rank * 2560 * 4:(rank + 1) * 2560 * 4])}
                    for rank in changed_ranks]
                details['shared_output_exact'] = serial_out[:2560 * 4] == batch_out[:2560 * 4]
                details['combined_output_exact'] = serial_out[2560 * 4:] == batch_out[2560 * 4:]
                details['combined_output_delta'] = (
                    None if details['combined_output_exact'] else
                    vector_delta(serial_out[2560 * 4:], batch_out[2560 * 4:]))
            else:
                details['output_comparison'] = 'unpaired because input activation or route weights differ'
            moe_rows[f'prompt{prompt}_position{position}'] = details

    result = {
        'scope': 'one current-source two-live target-only diagnostic with expert-11-first profile',
        'position_pair': [68, 71], 'model_layer': 4,
        'native_cpu_q8_1_dot_selector': args.q8_1_selector,
        'profile_sha256': profile_hash,
        'binary_sha256': hashlib.sha256(Path('build/integration/candidate/strata').read_bytes()).hexdigest(),
        'minimum_available_bytes': supervision['minimum_available_bytes'],
        'minimum_admission_available_bytes': supervision['minimum_admission_available_bytes'],
        'memory_samples': samples, 'maximum_cgroup_events': dict(event_max),
        'token_streams_match_serial_for_both_requests': True,
        'route_join': {
            'mapping': {'prompt0': route_map[(0, 71)], 'prompt1': route_map[(1, 71)]},
            'position68_missing_slot_inferred_by_complement': bool(missing68),
            'position71_slots_explicit': True,
            'route_ids_exact_at_both_positions': True,
            'weights_exact': {f'prompt{p}_position{pos}': exact
                              for (p, pos), exact in route_weights_exact.items()},
        },
        'committed_state': state_report,
        'layer4_rows': moe_rows,
        'interpretation_limit': 'only same-input rows with exact routes and router weights receive an output comparison. Position-68 owner changes and later committed-state differences are bounded to this two-request sequence; no general multi-live correctness claim follows.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
