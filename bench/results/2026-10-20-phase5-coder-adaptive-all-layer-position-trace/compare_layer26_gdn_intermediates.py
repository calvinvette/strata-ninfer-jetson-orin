#!/usr/bin/env python3
"""Compare selected layer-26 GDN verifier intermediates at position 511."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiiqQQQQQ8i')
FIELDS = ('x', 'qkv', 'h', 'gate', 'beta', 'z', 'y', 'gdn_out', 'ffn_x', 'ffn_y')


def parse_records(path):
    data = path.read_bytes()
    records = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f'truncated GDN header in {path} at {offset}')
        values = HEADER.unpack_from(data, offset)
        magic, version, layer, rows, pos0, n_embd, conv, v_heads, value_dim, state_floats, *tokens = values
        offset += HEADER.size
        if magic != b'STGDIAG4' or version != 4 or layer != 26 or rows != 1:
            raise ValueError(f'invalid GDN record header: {values[:10]}')
        counts = (n_embd, conv, conv, v_heads, v_heads, value_dim, value_dim,
                  n_embd, n_embd, n_embd)
        arrays = {}
        for name, count in zip(FIELDS, counts):
            size = count * 4
            if len(data) - offset < size:
                raise ValueError(f'truncated GDN field {name} in {path} at {offset}')
            raw = data[offset:offset + size]
            arrays[name] = struct.unpack(f'<{count}f', raw)
            offset += size
        records.append({'pos0': pos0, 'token': tokens[0], 'n_embd': n_embd,
                        'conv': conv, 'v_heads': v_heads, 'value_dim': value_dim,
                        'state_floats': state_floats, 'arrays': arrays})
    selected = [r for r in records if r['pos0'] == 511]
    if len(selected) != 2:
        raise ValueError(f'expected initial/recovery rows at position 511 in {path}, found {len(selected)}')
    return selected


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
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    initial, recovery = parse_records(args.run / 'verify-gdn.bin')
    if initial['token'] != 271 or recovery['token'] != 271:
        raise ValueError(f'unexpected token IDs: {initial["token"]}, {recovery["token"]}')
    if any(initial[key] != recovery[key] for key in ('n_embd', 'conv', 'v_heads', 'value_dim', 'state_floats')):
        raise ValueError('GDN capture shapes differ')
    fields = {name: summarize(initial['arrays'][name], recovery['arrays'][name]) for name in FIELDS}
    changed = [name for name in FIELDS if fields[name]['different_values']]
    result = {
        'scope': 'same-service initial/recovery Coder IQ1_M verifier GDN intermediates at layer 26',
        'position': 511,
        'token_id': 271,
        'model_shape': {key: initial[key] for key in ('n_embd', 'conv', 'v_heads', 'value_dim', 'state_floats')},
        'fields': fields,
        'first_differing_field_in_capture_order': changed[0] if changed else None,
        'all_fields_bitwise_identical': not changed,
        'limits': ['the layer-26 persistent GDN state before and after this individual token was not captured']
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'first_differing_field_in_capture_order': result['first_differing_field_in_capture_order'],
                      'fields': {name: {k: v for k, v in summary.items() if k != 'initial_f32_sha256' and k != 'recovery_f32_sha256'}
                                 for name, summary in fields.items()}}, indent=2))


if __name__ == '__main__':
    main()
