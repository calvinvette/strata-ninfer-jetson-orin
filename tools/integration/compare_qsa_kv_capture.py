#!/usr/bin/env python3
"""Compare opt-in dequantized selected-QSA-cache captures."""

import argparse
from array import array
import json
import math
import struct
from pathlib import Path
import sys

HEADER = struct.Struct("<8sIiqQQQii")


def read_capture(path):
    raw = Path(path).read_bytes()
    if len(raw) < HEADER.size:
        raise ValueError(f"{path}: truncated header")
    magic, version, layer, position, n_kv, head_dim, capacity, token, valid_count = HEADER.unpack_from(raw)
    if magic != b"STQKVD1\0" or version != 1:
        raise ValueError(f"{path}: unsupported selected-QSA-KV capture")
    if n_kv <= 0 or head_dim <= 0 or capacity <= 0 or not 0 <= valid_count <= capacity:
        raise ValueError(f"{path}: invalid dimensions or valid cell count")
    count = 2 * capacity * n_kv * head_dim
    expected = HEADER.size + count * 4
    if len(raw) != expected:
        raise ValueError(f"{path}: expected {expected} bytes, got {len(raw)}")
    data = array("f")
    data.frombytes(raw[HEADER.size:])
    if sys.byteorder != "little":
        data.byteswap()
    row_width = n_kv * head_dim
    return {
        "identity": (layer, position, n_kv, head_dim, capacity, token, valid_count),
        "data": data,
        "row_width": row_width,
    }


def metrics(a, b):
    delta = [x - y for x, y in zip(a, b)]
    denom = math.sqrt(sum(x * x for x in a))
    return {
        "count": len(a),
        "different": sum(x != y for x, y in zip(a, b)),
        "relative_l2": math.sqrt(sum(x * x for x in delta)) / max(denom, 1e-300),
        "max_abs": max((abs(x) for x in delta), default=0.0),
    }


def compare(reference, candidate):
    ref, cand = read_capture(reference), read_capture(candidate)
    if ref["identity"] != cand["identity"]:
        raise ValueError("capture identities or dimensions differ")
    layer, position, n_kv, head_dim, capacity, token, valid_count = ref["identity"]
    n = valid_count * ref["row_width"]
    total = capacity * ref["row_width"]
    r, c = ref["data"], cand["data"]
    return {
        "layer": layer,
        "position": position,
        "token": token,
        "valid_count": valid_count,
        "selection_payload_capacity": capacity,
        "key": metrics(r[:n], c[:n]),
        "value": metrics(r[total:total + n], c[total:total + n]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = compare(args.reference, args.candidate)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
