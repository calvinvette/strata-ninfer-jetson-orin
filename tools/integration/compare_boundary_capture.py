#!/usr/bin/env python3
"""Compare opt-in Strata residual-boundary captures from paired runs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct


HEADER = struct.Struct('<8sIiqQQii')


def read_capture(path: Path) -> tuple[dict, dict[str, tuple[float, ...]]]:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise ValueError(f'{path}: truncated boundary header')
    magic, version, layer, position, n_embd, hc, token, slot = HEADER.unpack_from(raw)
    if magic != b'STBNDY2\0' or version != 2 or layer < 0 or n_embd == 0 or hc == 0:
        raise ValueError(f'{path}: invalid STBNDY2 header')
    row = hc * n_embd + n_embd + hc
    total_floats = 2 * row + 2 * hc * n_embd
    if len(raw) != HEADER.size + total_floats * 4:
        raise ValueError(f'{path}: payload has {len(raw) - HEADER.size} bytes; expected {total_floats * 4}')
    values = struct.unpack_from(f'<{total_floats}f', raw, HEADER.size)
    width = hc * n_embd
    fields = {
        'layer_output_rt': values[:width],
        'layer_output_moe': values[width:width + n_embd],
        'layer_output_inj2': values[width + n_embd:row],
        'next_layer_rt': values[row:row + width],
        'next_layer_moe': values[row + width:row + width + n_embd],
        'next_layer_inj2': values[row + width + n_embd:2 * row],
        'next_layer_postread_rt': values[2 * row:2 * row + width],
        'next_layer_xn': values[2 * row + width:],
    }
    return ({'layer': layer, 'position': position, 'n_embd': n_embd, 'hc': hc,
             'token': token, 'slot': slot}, fields)


def metrics(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate):
        raise ValueError('boundary field dimensions differ')
    err2 = math.fsum((b - a) ** 2 for a, b in zip(reference, candidate))
    ref2 = math.fsum(a * a for a in reference)
    return {'count': len(reference), 'different': sum(a != b for a, b in zip(reference, candidate)),
            'relative_l2': math.sqrt(err2 / ref2) if ref2 else 0.0,
            'max_abs': max((abs(b - a) for a, b in zip(reference, candidate)), default=0.0)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ah, a = read_capture(args.reference)
    bh, b = read_capture(args.candidate)
    if ah != bh:
        raise ValueError(f'capture headers differ: {ah} vs {bh}')
    result = {'schema': 1, 'header': ah,
              'fields': {name: metrics(a[name], b[name]) for name in a}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'layer': ah['layer'], 'position': ah['position'],
                      'different_fields': [k for k, v in result['fields'].items() if v['different']]}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
