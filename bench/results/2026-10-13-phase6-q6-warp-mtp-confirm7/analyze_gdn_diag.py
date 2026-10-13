#!/usr/bin/env python3
"""Compare appended GDN capture streams by position and token."""
import argparse
import json
import struct
from pathlib import Path

import numpy as np

FMT = "<8sIiiqQQQQQ8i"
HEADER_BYTES = struct.calcsize(FMT)
FIELDS = ("x", "qkv", "h", "gate", "beta", "z", "y")


def read_records(path):
    data = Path(path).read_bytes()
    offset = 0
    records = []
    while offset < len(data):
        if offset + HEADER_BYTES > len(data):
            raise ValueError("truncated GDN diagnostic header")
        magic, version, layer, rows, pos0, n, c, hv, zv, state_n, *tokens = struct.unpack_from(FMT, data, offset)
        if (magic, version) not in ((b"STGDIAG1", 1), (b"STGDIAG2", 2), (b"STGDIAG3", 3),
                                    (b"STGDIAG4", 4)) or not 0 < rows <= 8:
            raise ValueError(f"unsupported GDN diagnostic record at byte {offset}")
        offset += HEADER_BYTES
        extra_counts = (state_n,) if version < 3 else (rows * n,) * (version - 1)
        counts = (rows * n, rows * c, rows * c, rows * hv, rows * hv, rows * zv, rows * zv, *extra_counts)
        arrays = []
        for count in counts:
            size = count * 4
            if offset + size > len(data):
                raise ValueError("truncated GDN diagnostic payload")
            arrays.append(np.frombuffer(data, dtype="<f4", count=count, offset=offset).copy())
            offset += size
        for row in range(rows):
            fields = {}
            dims = (n, c, c, hv, hv, zv, zv)
            for name, arr, dim in zip(FIELDS, arrays, dims):
                fields[name] = arr[row * dim:(row + 1) * dim]
            fields["gdn_out"] = arrays[-1][row * n:(row + 1) * n] if version == 2 else (
                arrays[-(version - 1)][row * n:(row + 1) * n] if version >= 3 else None)
            fields["ffn_x"] = arrays[-1][row * n:(row + 1) * n] if version == 3 else (
                arrays[-2][row * n:(row + 1) * n] if version >= 4 else None)
            fields["ffn_y"] = arrays[-1][row * n:(row + 1) * n] if version >= 4 else None
            records.append({"position": pos0 + row, "token": tokens[row], "fields": fields})
    return layer, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="file containing two appended engine captures")
    args = parser.parse_args()
    layer, records = read_records(args.path)
    # The capture harness appends all baseline windows, then candidate windows.
    second_start = next((i for i, r in enumerate(records[1:], 1)
                         if r["position"] == records[0]["position"]), None)
    if second_start is None:
        raise SystemExit("could not find second capture stream")
    arms = records[:second_start], records[second_start:]
    baseline = {(r["position"], r["token"]): r["fields"] for r in arms[0]}
    candidate = {(r["position"], r["token"]): r["fields"] for r in arms[1]}
    common = sorted(baseline.keys() & candidate.keys())
    first = None
    for key in common:
        differences = {}
        for field in (*FIELDS, "gdn_out", "ffn_x", "ffn_y"):
            a, b = baseline[key][field], candidate[key][field]
            if a is not None and b is not None and not np.array_equal(a, b):
                differences[field] = {
                    "different_values": int(np.count_nonzero(a != b)),
                    "relative_l2": float(np.linalg.norm(a - b) / max(np.linalg.norm(a), 1e-30)),
                    "max_abs": float(np.max(np.abs(a - b))),
                }
        if differences:
            first = {"position": key[0], "token": key[1], "fields": differences}
            break
    print(json.dumps({"layer": layer, "baseline_rows": len(arms[0]), "candidate_rows": len(arms[1]),
                      "common_rows": len(common), "first_activation_difference": first}, indent=2))


if __name__ == "__main__":
    main()
