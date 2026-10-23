#!/usr/bin/env python3
"""Compare selected GDN verifier intermediates across initial/recovery."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiiqQQQQQ8i')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')


def parse_records(path, layer, positions):
    data = path.read_bytes()
    records = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated GDN header in {path} at {offset}')
        values = HEADER.unpack_from(data, offset)
        magic, version, record_layer, rows, pos0, n_embd, conv, v_heads, value_dim, state_floats, *tokens = values
        offset += HEADER.size
        if magic != b'STGDIAG4' or version != 4 or record_layer != layer or not 0 < rows <= 8:
            raise ValueError(f'invalid GDN record header: {values[:10]}')
        counts = (n_embd, conv, conv, v_heads, v_heads, value_dim, value_dim,
                  n_embd, n_embd, n_embd)
        arrays = {}
        for name, count in zip(FIELDS, counts):
            values_count = rows * count
            size = values_count * 4
            if len(data) - offset < size:
                raise ValueError(f'truncated GDN field {name} in {path} at {offset}')
            arrays[name] = struct.unpack(f'<{values_count}f', data[offset:offset + size])
            offset += size
        shape = {'n_embd': n_embd, 'conv': conv, 'v_heads': v_heads,
                 'value_dim': value_dim, 'state_floats': state_floats}
        for row in range(rows):
            position = pos0 + row
            if position not in positions:
                continue
            row_arrays = {name: values[row * count:(row + 1) * count]
                          for name, values, count in zip(FIELDS, arrays.values(), counts)}
            records.append({'position': position, 'token': tokens[row], 'shape': shape,
                            'arrays': row_arrays})
    return data, records


def summarize(a, b):
    if len(a) != len(b):
        raise ValueError('GDN field lengths differ')
    if any(not math.isfinite(x) for x in a + b):
        raise ValueError('GDN capture contains a non-finite value')
    diff = [float(y) - float(x) for x, y in zip(a, b)]
    ref_sq = math.fsum(float(x) * float(x) for x in a)
    delta_sq = math.fsum(d * d for d in diff)
    return {
        'values': len(a),
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs_diff': max((abs(x) for x in diff), default=0.0),
        'relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None,
        'initial_f32_sha256': hashlib.sha256(struct.pack(f'<{len(a)}f', *a)).hexdigest(),
        'recovery_f32_sha256': hashlib.sha256(struct.pack(f'<{len(b)}f', *b)).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--layer', type=int, default=26)
    parser.add_argument('--positions', type=int, nargs='+', default=[511])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if any(p < 0 for p in args.positions) or args.positions != sorted(set(args.positions)):
        parser.error('--positions must be strictly increasing non-negative integers')

    if not 0 <= args.layer < 48:
        parser.error('--layer must be in [0, 47]')
    raw, records = parse_records(args.run / 'verify-gdn.bin', args.layer, set(args.positions))
    api_requests = json.loads((args.run / 'requests.json').read_text())['requests']
    grouped = {}
    for record in records:
        grouped.setdefault(record['position'], []).append(record)
    if set(grouped) != set(args.positions):
        raise ValueError(f'expected captures for positions {args.positions}; observed '
                         f'{ {position: len(pair) for position, pair in grouped.items()} }')
    eligible_by_position = {
        position: [request for request in api_requests
                   if position < request['prompt_tokens'] + len(request['ids'])]
        for position in args.positions
    }
    for position, pair in grouped.items():
        expected = len(eligible_by_position[position])
        if len(pair) != expected or expected not in (2, 3):
            raise ValueError(f'position {position}: found {len(pair)} intermediate records; expected '
                             f'{expected} from requests that reach the position. A capture limit or '
                             'prompt-cache reuse may have omitted a request, so initial/recovery cannot '
                             'be paired safely.')

    comparisons = {}
    for position in args.positions:
        pair = grouped[position]
        initial, recovery = pair[0], pair[-1]
        if initial['token'] != recovery['token'] or initial['shape'] != recovery['shape']:
            raise ValueError(f'initial/recovery metadata differs at position {position}')
        fields = {name: summarize(initial['arrays'][name], recovery['arrays'][name]) for name in FIELDS}
        changed = [name for name in FIELDS if fields[name]['different_values']]
        comparison = {
            'token_id': initial['token'],
            'first_differing_field_in_capture_order': changed[0] if changed else None,
            'all_fields_bitwise_identical': not changed,
            'request_record_count': len(pair),
            'captured_requests': [request['name'] for request in eligible_by_position[position]],
            'fields': fields,
        }
        if len(pair) == 3:
            transitions = []
            for left, right in ((0, 1), (1, 2)):
                a, b = pair[left], pair[right]
                transition_fields = {name: summarize(a['arrays'][name], b['arrays'][name])
                                     for name in FIELDS}
                transition_changed = [name for name in FIELDS
                                      if transition_fields[name]['different_values']]
                transitions.append({
                    'request_pair': [eligible_by_position[position][left]['name'],
                                     eligible_by_position[position][right]['name']],
                    'token_ids_equal': a['token'] == b['token'],
                    'first_differing_field_in_capture_order':
                        transition_changed[0] if transition_changed else None,
                    'all_fields_bitwise_identical': not transition_changed,
                    'fields': transition_fields,
                })
            comparison['request_transitions'] = transitions
        comparisons[str(position)] = comparison

    result = {
        'scope': f'same-service layer-{args.layer} GDN verifier intermediates at selected token positions',
        'layer': args.layer,
        'positions': args.positions,
        'model_shape': records[0]['shape'],
        'raw_capture_bytes': len(raw),
        'raw_capture_sha256': hashlib.sha256(raw).hexdigest(),
        'position_comparisons': comparisons,
        'limits': ['GDN persistent state before and after each token is not part of this intermediate capture'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'positions': args.positions,
                      'first_differing_field_by_position': {
                          position: item['first_differing_field_in_capture_order']
                          for position, item in comparisons.items()},
                      'raw_capture_bytes': len(raw),
                      'raw_capture_sha256': result['raw_capture_sha256']}, indent=2))


if __name__ == '__main__':
    main()
