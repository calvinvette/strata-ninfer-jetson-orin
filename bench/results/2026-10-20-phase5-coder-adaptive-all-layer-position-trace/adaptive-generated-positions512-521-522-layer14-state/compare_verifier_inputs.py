#!/usr/bin/env python3
"""Compare selected-position CUDA verifier inputs across paired requests."""
import argparse
import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

HEADER = struct.Struct('<8sIIIIQq8i')
LAYERS = 48
WIDTH = 2560


def read_inputs(path, positions, expected_layers, request_count):
    raw = path.read_bytes()
    offset = 0
    grouped = defaultdict(list)
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f'{path}: truncated verifier input header')
        magic, version, layer, rows, reserved, width, pos0, *tokens = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if (magic != b'STMOINP1' or version != 1 or layer not in expected_layers or
                not 0 < rows <= 8 or reserved != 0 or width != WIDTH or
                not 0 <= layer < LAYERS):
            raise ValueError(f'{path}: invalid verifier input header for layer {layer}')
        nbytes = rows * WIDTH * 4
        payload = raw[offset:offset + nbytes]
        if len(payload) != nbytes:
            raise ValueError(f'{path}: truncated verifier input payload')
        offset += nbytes
        for values in struct.iter_unpack('<f', payload):
            if not math.isfinite(values[0]):
                raise ValueError(f'{path}: non-finite value at layer {layer}, position {pos0}')
        for row in range(rows):
            position = pos0 + row
            if position not in positions:
                continue
            start = row * WIDTH * 4
            tensor = payload[start:start + WIDTH * 4]
            token = tokens[row]
            grouped[(position, layer)].append((token, tensor))
    expected_keys = {(position, layer) for position in positions for layer in expected_layers}
    if set(grouped) != expected_keys:
        missing = sorted(expected_keys - set(grouped))
        extra = sorted(set(grouped) - expected_keys)
        raise ValueError(f'{path}: missing {missing[:8]} or unexpected {extra[:8]} layer/position keys')
    for key, records in grouped.items():
        if len(records) != request_count:
            raise ValueError(f'{path}: {key} expected {request_count} request records, got {len(records)}')
    return grouped


def summarize(left, right):
    a = struct.unpack(f'<{WIDTH}f', left)
    b = struct.unpack(f'<{WIDTH}f', right)
    delta = [float(x) - float(y) for x, y in zip(a, b)]
    denom = math.fsum(float(x) ** 2 for x in b)
    return {
        'bitwise_equal': left == right,
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs_diff': max(map(abs, delta), default=0.0),
        'relative_l2': math.sqrt(math.fsum(x * x for x in delta) / denom) if denom else None,
        'left_sha256': hashlib.sha256(left).hexdigest(),
        'right_sha256': hashlib.sha256(right).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    campaign = json.loads((args.run_dir / 'campaign.json').read_text())
    if campaign.get('status') != 'pass':
        raise ValueError('paired campaign did not pass')
    request_names = [row['name'] for row in campaign['runs'][0]['analysis']['requests']]
    positions = set(campaign['verify_moe_positions'])
    if not positions:
        raise ValueError('campaign has no selected verifier positions')
    layers = set(range(LAYERS)) if campaign['verify_moe_input_layers'] == 'all' else {
        campaign['capture_verify_moe_layer']
    }
    result = {
        'scope': 'CUDA-side verifier MoE input tensors at selected generated positions',
        'width': WIDTH,
        'model_repository': campaign['model_repository'],
        'model_revision': campaign['model_revision'],
        'quantization': campaign['quantization'],
        'positions': sorted(positions),
        'requests': request_names,
        'arms': {},
    }
    transitions = [(i, i + 1, f'{request_names[i]}_to_{request_names[i + 1]}')
                   for i in range(len(request_names) - 1)]
    transitions.append((0, min(2, len(request_names) - 1), f'{request_names[0]}_to_{request_names[min(2, len(request_names)-1)]}'))
    for arm in ('adaptive-cap8', 'delayed-control'):
        tensors = read_inputs(args.run_dir / arm / 'result' / 'verify-moe-input.bin',
                              positions, layers, len(request_names))
        arm_result = {'record_count': sum(map(len, tensors.values())), 'positions': {}}
        for position in sorted(positions):
            position_result = {}
            for left, right, name in transitions:
                differences = {}
                for layer in sorted(layers):
                    a_token, a_tensor = tensors[(position, layer)][left]
                    b_token, b_tensor = tensors[(position, layer)][right]
                    if a_token != b_token:
                        raise ValueError(f'{arm} position {position}, layer {layer}: request token IDs differ')
                    if a_tensor != b_tensor:
                        differences[str(layer)] = summarize(a_tensor, b_tensor)
                position_result[name] = {
                    'different_layer_count': len(differences),
                    'first_different_layer': min(map(int, differences), default=None),
                    'layers': differences,
                }
            arm_result['positions'][str(position)] = position_result
        result['arms'][arm] = arm_result
    output = args.run_dir / 'verifier-input-analysis.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({arm: {position: {
        name: {'different_layer_count': row['different_layer_count'],
               'first_different_layer': row['first_different_layer']}
        for name, row in values.items()
    } for position, values in data['positions'].items()}
        for arm, data in result['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
