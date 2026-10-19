#!/usr/bin/env python3
"""Compare selected layer-26 GDN verifier intermediates across initial/recovery."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiiqQQQQQ8i')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')


def parse_records(path, positions):
    data = path.read_bytes()
    records = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated GDN header in {path} at {offset}')
        values = HEADER.unpack_from(data, offset)
        magic, version, layer, rows, pos0, n_embd, conv, v_heads, value_dim, state_floats, *tokens = values
        offset += HEADER.size
        if magic != b'STGDIAG4' or version != 4 or layer != 26 or not 0 < rows <= 8:
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
    parser.add_argument('--positions', type=int, nargs='+', default=[511])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if any(p < 0 for p in args.positions) or args.positions != sorted(set(args.positions)):
        parser.error('--positions must be strictly increasing non-negative integers')

    raw, records = parse_records(args.run / 'verify-gdn.bin', set(args.positions))
    grouped = {}
    for record in records:
        grouped.setdefault(record['position'], []).append(record)
    if set(grouped) != set(args.positions) or any(len(pair) != 2 for pair in grouped.values()):
        raise ValueError(f'expected initial/recovery intermediates for {args.positions}; observed '
                         f'{ {position: len(pair) for position, pair in grouped.items()} }')

    comparisons = {}
    for position in args.positions:
        initial, recovery = grouped[position]
        if initial['token'] != recovery['token'] or initial['shape'] != recovery['shape']:
            raise ValueError(f'initial/recovery metadata differs at position {position}')
        fields = {name: summarize(initial['arrays'][name], recovery['arrays'][name]) for name in FIELDS}
        changed = [name for name in FIELDS if fields[name]['different_values']]
        comparisons[str(position)] = {
            'token_id': initial['token'],
            'first_differing_field_in_capture_order': changed[0] if changed else None,
            'all_fields_bitwise_identical': not changed,
            'fields': fields,
        }

    result = {
        'scope': 'same-service layer-26 GDN verifier intermediates at selected token positions',
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
