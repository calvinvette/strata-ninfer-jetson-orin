"""Compare two Strata GDN float32 state dumps without loading whole-model state in RAM."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

HEADER = struct.Struct('<8sQQQ')
MAGIC = b'STGDN01\0'


def read_header(path: Path) -> tuple[int, int, int]:
    with path.open('rb') as stream:
        raw = stream.read(HEADER.size)
    if len(raw) != HEADER.size:
        raise ValueError(f'{path}: truncated GDN state header')
    magic, cells, layers, floats_per_layer = HEADER.unpack(raw)
    if magic != MAGIC:
        raise ValueError(f'{path}: unsupported GDN state magic {magic!r}')
    expected = HEADER.size + layers * floats_per_layer * 4
    actual = path.stat().st_size
    if actual != expected:
        raise ValueError(f'{path}: expected {expected} bytes from header, found {actual}')
    return cells, layers, floats_per_layer


def compare(reference: Path, candidate: Path) -> dict:
    ref_shape = read_header(reference)
    cand_shape = read_header(candidate)
    if ref_shape != cand_shape:
        raise ValueError(f'GDN state shapes differ: {ref_shape} vs {cand_shape}')
    cells, layers, floats_per_layer = ref_shape
    all_delta_sq = []
    all_ref_sq = []
    all_abs = []
    per_layer = []
    different = 0
    maximum = {'layer': -1, 'index': -1, 'max_abs': -1.0}
    ref_unpack = struct.Struct('<f').iter_unpack

    with reference.open('rb') as ref_stream, candidate.open('rb') as cand_stream:
        ref_stream.seek(HEADER.size)
        cand_stream.seek(HEADER.size)
        for layer in range(layers):
            byte_count = floats_per_layer * 4
            ref_bytes = ref_stream.read(byte_count)
            cand_bytes = cand_stream.read(byte_count)
            delta_squares = []
            ref_squares = []
            abs_deltas = []
            layer_different = 0
            layer_max_abs = -1.0
            layer_max_index = -1
            for index, (ra, cb) in enumerate(zip(ref_unpack(ref_bytes), ref_unpack(cand_bytes))):
                a, b = ra[0], cb[0]
                if not math.isfinite(a) or not math.isfinite(b):
                    raise ValueError(f'non-finite GDN value at layer {layer}, index {index}')
                delta = b - a
                abs_delta = abs(delta)
                if delta != 0.0:
                    layer_different += 1
                delta_squares.append(delta * delta)
                ref_squares.append(a * a)
                abs_deltas.append(abs_delta)
                if abs_delta > layer_max_abs:
                    layer_max_abs, layer_max_index = abs_delta, index
            layer_delta_sq = math.fsum(delta_squares)
            layer_ref_sq = math.fsum(ref_squares)
            layer_abs = math.fsum(abs_deltas)
            different += layer_different
            all_delta_sq.append(layer_delta_sq)
            all_ref_sq.append(layer_ref_sq)
            all_abs.append(layer_abs)
            relative = math.sqrt(layer_delta_sq / layer_ref_sq) if layer_ref_sq else None
            per_layer.append({
                'layer': layer,
                'relative_l2': relative,
                'rms_abs_delta': math.sqrt(layer_delta_sq / floats_per_layer),
                'mean_abs_delta': layer_abs / floats_per_layer,
                'max_abs_delta': layer_max_abs,
                'max_abs_index': layer_max_index,
                'exact_fraction': (floats_per_layer - layer_different) / floats_per_layer,
            })
            if layer_max_abs > maximum['max_abs']:
                maximum = {'layer': layer, 'index': layer_max_index, 'max_abs': layer_max_abs}

    total = layers * floats_per_layer
    delta_sq = math.fsum(all_delta_sq)
    ref_sq = math.fsum(all_ref_sq)
    abs_delta = math.fsum(all_abs)
    return {
        'schema': 1,
        'cells': cells,
        'layers': layers,
        'floats_per_layer': floats_per_layer,
        'total_floats': total,
        'different_floats': different,
        'fraction_different': different / total if total else 0.0,
        'global_rms_abs_delta': math.sqrt(delta_sq / total) if total else 0.0,
        'global_mean_abs_delta': abs_delta / total if total else 0.0,
        'global_relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None,
        'max_layer_relative_l2': max(per_layer, key=lambda row: row['relative_l2'] or -1.0),
        'max_element_error': maximum,
        'per_layer': per_layer,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        result = compare(args.reference, args.candidate)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(serialized)
    else:
        sys.stdout.write(serialized)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
