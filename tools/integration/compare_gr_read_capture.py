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
GDN_V4_HEADER = struct.Struct("<8sIiiqQQQQQ8i")
GDN_V5_HEADER = struct.Struct("<8sIiiqQQQQQ8q8i8i")


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


def read_gdn_x(path: Path) -> tuple[dict, tuple[float, ...]]:
    raw = path.read_bytes()
    if len(raw) < 12:
        raise ValueError(f"{path}: truncated GDN diagnostic header")
    magic = raw[:8]
    if magic == b"STGDIAG4":
        header_struct = GDN_V4_HEADER
        values = header_struct.unpack_from(raw)
        _, version, layer, rows, pos0, n_embd, conv, heads, value_dim, _state, *tokens = values
        position = pos0
        token = tokens[0]
    elif magic == b"STGDIAG5":
        header_struct = GDN_V5_HEADER
        values = header_struct.unpack_from(raw)
        _, version, layer, rows, pos0, n_embd, conv, heads, value_dim, _state, *tail = values
        positions, slots, tokens = tail[:8], tail[8:16], tail[16:24]
        position, token = positions[0], tokens[0]
    else:
        raise ValueError(f"{path}: expected STGDIAG4 or STGDIAG5")
    if version not in (4, 5) or rows != 1 or n_embd == 0 or conv == 0 or heads == 0 or value_dim == 0:
        raise ValueError(f"{path}: expected one valid GDN row")
    payload = raw[header_struct.size:]
    expected = (n_embd + 2 * conv + 2 * heads + 2 * value_dim + 3 * n_embd) * 4
    if len(payload) != expected:
        raise ValueError(f"{path}: payload has {len(payload)} bytes; expected {expected}")
    x = struct.unpack_from(f"<{n_embd}f", payload)
    return ({"layer": layer, "position": position, "token": token,
             "n_embd": n_embd, "slot": -1 if magic == b"STGDIAG4" else slots[0]}, x)


def compare(reference: Path, candidate: Path, strata_gdn: Path | None = None,
            ninfer_gdn: Path | None = None) -> dict:
    ah, a = read_capture(reference)
    bh, b = read_capture(candidate)
    if ah != bh:
        raise ValueError(f"capture headers differ: {ah} vs {bh}")
    result = {"schema": 1, "header": ah,
              "fields": {name: metrics(a[name], b[name]) for name in a},
              "first_differing_field": next((name for name in a if a[name] != b[name]), None)}
    if (strata_gdn is None) != (ninfer_gdn is None):
        raise ValueError("provide both GDN diagnostic paths or neither")
    if strata_gdn is not None and ninfer_gdn is not None:
        sg_header, sg_x = read_gdn_x(strata_gdn)
        ng_header, ng_x = read_gdn_x(ninfer_gdn)
        for label, header in (("Strata", sg_header), ("NInfer", ng_header)):
            for field in ("layer", "position", "token", "n_embd"):
                if header[field] != ah[field]:
                    raise ValueError(f"{label} GDN/read {field} mismatch: {header[field]} vs {ah[field]}")
        result["gdn_x_to_gr_mixed"] = {
            "strata": metrics(a["mixed"], sg_x),
            "ninfer": metrics(b["mixed"], ng_x),
        }
        result["gdn_x_cross_backend"] = metrics(sg_x, ng_x)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--strata-gdn", type=Path,
                        help="same-run STGDIAG4/5 capture from the Strata arm")
    parser.add_argument("--ninfer-gdn", type=Path,
                        help="same-run STGDIAG4/5 capture from the NInfer arm")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.reference, args.candidate, args.strata_gdn, args.ninfer_gdn)
    except (OSError, ValueError, struct.error) as exc:
        print(f"compare_gr_read_capture: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(json.dumps({"layer": result["header"]["layer"],
                      "position": result["header"]["position"],
                      "first_differing_field": result["first_differing_field"],
                      "gdn_x_to_gr_mixed": result.get("gdn_x_to_gr_mixed")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
