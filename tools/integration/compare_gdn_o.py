#!/usr/bin/env python3
"""Compare raw GDN recurrence outputs and normalized y rows by absolute position."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

O_HEADER = struct.Struct('<8sIiiqQ8i')
DIAG_HEADER_V4 = struct.Struct('<8sIiiqQQQQQ8i')


def metrics(a: bytes, b: bytes) -> dict:
    if len(a) != len(b) or len(a) % 4:
        raise ValueError('unpaired GDN float32 rows')
    changed = 0
    max_abs = 0.0
    err_sq = ref_sq = 0.0
    for (av,), (bv,) in zip(struct.iter_unpack('<f', a), struct.iter_unpack('<f', b)):
        if not math.isfinite(av) or not math.isfinite(bv):
            raise ValueError('non-finite value in GDN capture')
        delta = float(bv) - float(av)
        changed += av != bv
        max_abs = max(max_abs, abs(delta))
        err_sq += delta * delta
        ref_sq += float(av) * float(av)
    return {'values': len(a) // 4, 'different_values': changed, 'max_abs': max_abs,
            'relative_l2': math.sqrt(err_sq / ref_sq) if ref_sq else 0.0}


def read_o(path: Path) -> dict[int, tuple[int, bytes]]:
    rows: dict[int, tuple[int, bytes]] = {}
    with path.open('rb') as stream:
        while header := stream.read(O_HEADER.size):
            if len(header) != O_HEADER.size:
                raise ValueError(f'{path}: truncated raw-o header')
            magic, version, layer, count, pos0, value_dim, *tokens = O_HEADER.unpack(header)
            if magic != b'STGDOO1\0' or version != 1 or not 1 <= count <= len(tokens) or value_dim == 0:
                raise ValueError(f'{path}: invalid raw-o record header')
            for i in range(count):
                payload = stream.read(value_dim * 4)
                if len(payload) != value_dim * 4:
                    raise ValueError(f'{path}: truncated raw-o payload')
                pos = pos0 + i
                if pos in rows:
                    raise ValueError(f'{path}: duplicate raw-o position {pos}')
                rows[pos] = (tokens[i], payload)
    if not rows:
        raise ValueError(f'{path}: no raw-o records')
    return rows


def read_y(path: Path) -> dict[int, tuple[int, bytes]]:
    rows: dict[int, tuple[int, bytes]] = {}
    with path.open('rb') as stream:
        while header := stream.read(DIAG_HEADER_V4.size):
            if len(header) != DIAG_HEADER_V4.size:
                raise ValueError(f'{path}: truncated GDN diagnostic header')
            magic, version, layer, count, pos0, n, c, hv, zv, _state_floats, *tokens = DIAG_HEADER_V4.unpack(header)
            if magic != b'STGDIAG4' or version != 4 or not 1 <= count <= len(tokens):
                raise ValueError(f'{path}: expected STGDIAG4 records')
            sizes = [count*n, count*c, count*c, count*hv, count*hv, count*zv,
                     count*zv, count*n, count*n, count*n]
            y_offset_floats = sum(sizes[:6])
            payload_size = sum(sizes) * 4
            payload = stream.read(payload_size)
            if len(payload) != payload_size:
                raise ValueError(f'{path}: truncated GDN diagnostic payload')
            for i in range(count):
                pos = pos0 + i
                start = (y_offset_floats + i*zv) * 4
                end = start + zv * 4
                if pos in rows:
                    raise ValueError(f'{path}: duplicate y position {pos}')
                rows[pos] = (tokens[i], payload[start:end])
    if not rows:
        raise ValueError(f'{path}: no y records')
    return rows


def compare(o_a: Path, o_b: Path, y_a: Path, y_b: Path) -> dict:
    left_o, right_o = read_o(o_a), read_o(o_b)
    left_y, right_y = read_y(y_a), read_y(y_b)
    common = sorted(set(left_o) & set(right_o) & set(left_y) & set(right_y))
    if not common:
        raise ValueError('the four files contain no common token positions')
    result = []
    for pos in common:
        tokens = (left_o[pos][0], right_o[pos][0], left_y[pos][0], right_y[pos][0])
        if len(set(tokens)) != 1:
            raise ValueError(f'token mismatch at position {pos}: {tokens}')
        result.append({'position': pos, 'token': tokens[0],
                       'o': metrics(left_o[pos][1], right_o[pos][1]),
                       'y': metrics(left_y[pos][1], right_y[pos][1])})
    return {'schema': 1, 'positions_compared': len(result), 'position_range': [common[0], common[-1]],
            'first_o_difference': next((x['position'] for x in result if x['o']['different_values']), None),
            'first_y_difference': next((x['position'] for x in result if x['y']['different_values']), None),
            'records': result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strata-o', type=Path, required=True)
    parser.add_argument('--ninfer-o', type=Path, required=True)
    parser.add_argument('--strata-gdn', type=Path, required=True)
    parser.add_argument('--ninfer-gdn', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.strata_o, args.ninfer_o, args.strata_gdn, args.ninfer_gdn)
    except (OSError, ValueError) as exc:
        print(f'compare_gdn_o: {exc}', file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    sys.stdout.write(rendered)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
