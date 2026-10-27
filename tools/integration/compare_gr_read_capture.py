#!/usr/bin/env python3
"""Compare opt-in fused hyperconnection read captures from paired runs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

HEADER = struct.Struct("<8sIIqiiQQQ")


def read_capture(path: Path) -> tuple[dict, dict[str, tuple[float, ...]]]:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise ValueError(f"{path}: truncated fused GR-read header")
    magic, version, layer, position, token, reserved, n_embd, hc, hc_lr = HEADER.unpack_from(raw)
    if magic != b"STGRRD1\0" or version != 1 or n_embd == 0 or hc == 0:
        raise ValueError(f"{path}: invalid STGRRD1 header")
    count = hc * n_embd + hc_lr + 2 * hc + n_embd
    if len(raw) != HEADER.size + count * 4:
        raise ValueError(f"{path}: payload has {len(raw) - HEADER.size} bytes; expected {count * 4}")
    v = struct.unpack_from(f"<{count}f", raw, HEADER.size)
    i = 0
    fields = {}
    for name, width in (("xn", hc * n_embd), ("lo", hc_lr), ("rs", hc),
                        ("inj_out", hc), ("mixed", n_embd)):
        fields[name] = v[i:i + width]
        i += width
    return ({"layer": layer, "position": position, "token": token,
             "n_embd": n_embd, "hc": hc, "hc_lr": hc_lr}, fields)


def metrics(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate):
        raise ValueError("fused GR-read field dimensions differ")
    err_sq = math.fsum((b - a) ** 2 for a, b in zip(reference, candidate))
    ref_sq = math.fsum(a * a for a in reference)
    return {"count": len(reference), "different": sum(a != b for a, b in zip(reference, candidate)),
            "relative_l2": math.sqrt(err_sq / ref_sq) if ref_sq else math.sqrt(err_sq),
            "max_abs": max((abs(b - a) for a, b in zip(reference, candidate)), default=0.0)}


def compare(reference: Path, candidate: Path) -> dict:
    ah, a = read_capture(reference)
    bh, b = read_capture(candidate)
    if ah != bh:
        raise ValueError(f"capture headers differ: {ah} vs {bh}")
    return {"schema": 1, "header": ah,
            "fields": {name: metrics(a[name], b[name]) for name in a},
            "first_differing_field": next((name for name in a if a[name] != b[name]), None)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.reference, args.candidate)
    except (OSError, ValueError, struct.error) as exc:
        print(f"compare_gr_read_capture: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(json.dumps({"layer": result["header"]["layer"],
                      "position": result["header"]["position"],
                      "first_differing_field": result["first_differing_field"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
