#!/usr/bin/env python3
"""Extract the verifier's device-side MoE input row from STGDIAG4 captures."""
import argparse
import json
import pathlib
import struct

HEADER = struct.Struct('<8sIiiqQQQQQ8i')
ap = argparse.ArgumentParser()
ap.add_argument('output', type=pathlib.Path)
ap.add_argument('--position', type=int, required=True)
ap.add_argument('--token', type=int, required=True)
ap.add_argument('--layer', type=int, default=1)
ap.add_argument('--arms', nargs='+', default=['cpu_mirror', 'gpu_layer1'])
args = ap.parse_args()
root = pathlib.Path(__file__).resolve().parents[3]
base = root / 'bench/results/2026-10-18-phase5-coder-layer1-route-isolation/position-keyed-three-arm'

def find_row(path):
    data = path.read_bytes()
    offset = 0
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError(f'{path}: truncated header')
        magic, version, layer, rows, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b'STGDIAG4' or version != 4 or not 0 < rows <= 8:
            raise ValueError(f'{path}: unsupported GDN diagnostic record')
        counts_before_gdn_out = rows * n + 2 * rows * c + 2 * rows * hv + 2 * rows * zv
        ffn_x_offset = offset + (counts_before_gdn_out + rows * n) * 4
        payload_bytes = rows * (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        if offset + payload_bytes > len(data):
            raise ValueError(f'{path}: truncated payload')
        for row in range(rows):
            if layer == args.layer and pos0 + row == args.position and tokens[row] == args.token:
                values = struct.unpack_from(f'<{n}f', data, ffn_x_offset + row * n * 4)
                return values
        offset += payload_bytes
    raise ValueError(f'{path}: no layer {args.layer} row at {args.position}/{args.token}')

vectors = {arm: find_row(base / arm / 'result/combined-moe.bin') for arm in args.arms}
ref_arm = args.arms[0]
if any(v != vectors[ref_arm] for v in vectors.values()):
    raise SystemExit('device-captured MoE input rows differ across requested arms')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_bytes(struct.pack('<' + 'f' * len(vectors[ref_arm]), *vectors[ref_arm]))
meta = {'layer': args.layer, 'position': args.position, 'token_id': args.token,
        'n_embd': len(vectors[ref_arm]), 'device_ffn_x_equal_across_arms': args.arms,
        'output': str(args.output)}
args.output.with_suffix(args.output.suffix + '.json').write_text(json.dumps(meta, indent=2) + '\n')
print(json.dumps(meta, indent=2))
