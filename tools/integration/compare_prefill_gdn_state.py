#!/usr/bin/env python3
"""Compare captured end-of-prompt GDN state snapshots from paired runs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys


HEADER = struct.Struct('<8sIiqQQi4x')
MAGIC = b'STPFGS1\0'


def read_records(path: Path) -> dict[tuple[int, int], tuple[tuple, bytes]]:
    records = {}
    with path.open('rb') as stream:
        while raw := stream.read(HEADER.size):
            if len(raw) != HEADER.size:
                raise ValueError(f'{path}: truncated prefill GDN header')
            magic, version, layer, boundary, recurrent, count, prompt_tokens = HEADER.unpack(raw)
            if magic != MAGIC or version != 1 or layer < 0 or not count or recurrent > count:
                raise ValueError(f'{path}: invalid prefill GDN header')
            payload = stream.read(count * 4)
            if len(payload) != count * 4:
                raise ValueError(f'{path}: truncated prefill GDN payload')
            key = (layer, boundary)
            if key in records:
                raise ValueError(f'{path}: duplicate layer/boundary {key}')
            records[key] = ((version, layer, boundary, recurrent, count, prompt_tokens), payload)
    if not records:
        raise ValueError(f'{path}: no prefill GDN records')
    return records


def compare_values(reference: bytes, candidate: bytes) -> dict:
    if len(reference) != len(candidate) or len(reference) % 4:
        raise ValueError('prefill GDN payload dimensions differ')
    count = changed = 0
    error_sq = reference_sq = 0.0
    max_abs = 0.0
    for (a,), (b,) in zip(struct.iter_unpack('<f', reference), struct.iter_unpack('<f', candidate)):
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError('non-finite value in prefill GDN state')
        delta = float(b) - float(a)
        changed += a != b
        error_sq += delta * delta
        reference_sq += float(a) * float(a)
        max_abs = max(max_abs, abs(delta))
        count += 1
    return {'values': count, 'different_values': changed,
            'relative_l2': math.sqrt(error_sq / reference_sq) if reference_sq else 0.0,
            'rms_abs_delta': math.sqrt(error_sq / count) if count else 0.0,
            'max_abs_delta': max_abs}


def compare(reference: Path, candidate: Path) -> dict:
    ref, cand = read_records(reference), read_records(candidate)
    if ref.keys() != cand.keys():
        raise ValueError(f'prefill GDN layer/boundary records differ: {sorted(ref)} vs {sorted(cand)}')
    rows = []
    for key in sorted(ref):
        rh, rv = ref[key]
        ch, cv = cand[key]
        if rh != ch:
            raise ValueError(f'prefill GDN headers differ at layer/boundary {key}')
        rows.append({'layer': key[0], 'boundary': key[1], 'prompt_tokens': rh[5],
                     **compare_values(rv, cv)})
    return {'schema': 1, 'format': 'STPFGS1', 'records': rows,
            'first_differing_layer': next((r['layer'] for r in rows if r['different_values']), None)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.reference, args.candidate)
    except (OSError, ValueError, struct.error) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    sys.stdout.write(rendered)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
