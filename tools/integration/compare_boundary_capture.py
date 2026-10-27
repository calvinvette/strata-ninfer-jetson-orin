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
    records = read_capture_records(path)
    if len(records) != 1:
        raise ValueError(f'{path}: expected one boundary record, found {len(records)}')
    return records[0]


def read_capture_records(path: Path) -> list[tuple[dict, dict[str, tuple[float, ...]]]]:
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f'{path}: truncated boundary header')
        magic, version, layer, position, n_embd, hc, token, slot = HEADER.unpack_from(raw, offset)
        if magic != b'STBNDY2\0' or version != 2 or layer < 0 or n_embd == 0 or hc == 0:
            raise ValueError(f'{path}: invalid STBNDY2 header at byte {offset}')
        row = hc * n_embd + n_embd + hc
        total_floats = 2 * row + 2 * hc * n_embd
        record_size = HEADER.size + total_floats * 4
        if len(raw) - offset < record_size:
            raise ValueError(f'{path}: truncated boundary payload at byte {offset}')
        values = struct.unpack_from(f'<{total_floats}f', raw, offset + HEADER.size)
        records.append(_decode_record(layer, position, n_embd, hc, token, slot, values))
        offset += record_size
    if not records:
        raise ValueError(f'{path}: empty boundary capture')
    return records


def _decode_record(layer, position, n_embd, hc, token, slot, values):
    row = hc * n_embd + n_embd + hc
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
    ar = read_capture_records(args.reference)
    br = read_capture_records(args.candidate)
    amap = {h['layer']: (h, f) for h, f in ar}
    bmap = {h['layer']: (h, f) for h, f in br}
    if len(amap) != len(ar) or len(bmap) != len(br) or amap.keys() != bmap.keys():
        raise ValueError('capture layer sets differ or contain duplicates')
    compared = []
    for layer in sorted(amap):
        ah, a = amap[layer]
        bh, b = bmap[layer]
        if ah != bh:
            raise ValueError(f'capture headers differ at layer {layer}: {ah} vs {bh}')
        compared.append({'header': ah, 'fields': {name: metrics(a[name], b[name]) for name in a}})
    result = {'schema': 2 if len(compared) > 1 else 1,
              'header': compared[0]['header'], 'fields': compared[0]['fields']}
    if len(compared) > 1:
        result['records'] = compared
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'layers': [{'layer': r['header']['layer'],
                                  'different_fields': [k for k, v in r['fields'].items() if v['different']]}
                                 for r in compared]}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
