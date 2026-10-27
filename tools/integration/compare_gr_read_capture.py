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


def _decode_capture(raw: bytes, path: Path) -> tuple[dict, dict[str, tuple[float, ...]]]:
    if len(raw) < HEADER.size:
        raise ValueError(f"{path}: truncated fused GR-read header")
    magic, version, layer, position, token, reserved, n_embd, hc, hc_lr = HEADER.unpack_from(raw)
    if magic not in (b"STGRRD1\0", b"STGRRD2\0") or version not in (1, 2) or n_embd == 0 or hc == 0:
        raise ValueError(f"{path}: invalid fused GR-read header")
    if (magic, version) not in ((b"STGRRD1\0", 1), (b"STGRRD2\0", 2)):
        raise ValueError(f"{path}: fused GR-read magic and version disagree")
    count = hc * n_embd + hc_lr + 2 * hc + n_embd + (n_embd if version == 2 else 0)
    if len(raw) != HEADER.size + count * 4:
        raise ValueError(f"{path}: payload has {len(raw) - HEADER.size} bytes; expected {count * 4}")
    v = struct.unpack_from(f"<{count}f", raw, HEADER.size)
    i = 0
    fields = {}
    layout = (("R", n_embd), ("xn", hc * n_embd), ("lo", hc_lr),
              ("rs", hc), ("inj_out", hc), ("mixed", n_embd)) if version == 2 else (
              ("xn", hc * n_embd), ("lo", hc_lr), ("rs", hc),
              ("inj_out", hc), ("mixed", n_embd))
    for name, width in layout:
        fields[name] = v[i:i + width]
        i += width
    return ({"version": version, "layer": layer, "position": position, "token": token,
             "n_embd": n_embd, "hc": hc, "hc_lr": hc_lr}, fields)


def read_capture_records(path: Path) -> dict[int, tuple[dict, dict[str, tuple[float, ...]]]]:
    raw = path.read_bytes()
    records = {}
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f"{path}: truncated fused GR-read header")
        magic, version, _layer, position, _token, _reserved, n_embd, hc, hc_lr = HEADER.unpack_from(raw, offset)
        if magic not in (b"STGRRD1\0", b"STGRRD2\0") or version not in (1, 2):
            raise ValueError(f"{path}: invalid fused GR-read record at byte {offset}")
        count = hc * n_embd + hc_lr + 2 * hc + n_embd + (n_embd if version == 2 else 0)
        record_size = HEADER.size + count * 4
        if len(raw) - offset < record_size:
            raise ValueError(f"{path}: truncated fused GR-read payload")
        header, fields = _decode_capture(raw[offset:offset + record_size], path)
        if position in records:
            raise ValueError(f"{path}: duplicate fused GR-read row for position {position}")
        records[position] = (header, fields)
        offset += record_size
    if not records:
        raise ValueError(f"{path}: no fused GR-read records")
    return records


def read_capture(path: Path) -> tuple[dict, dict[str, tuple[float, ...]]]:
    records = read_capture_records(path)
    if len(records) != 1:
        raise ValueError(f"{path}: expected one fused GR-read record, found {len(records)}")
    return next(iter(records.values()))


def metrics(reference: tuple[float, ...], candidate: tuple[float, ...]) -> dict:
    if len(reference) != len(candidate):
        raise ValueError("fused GR-read field dimensions differ")
    err_sq = math.fsum((b - a) ** 2 for a, b in zip(reference, candidate))
    ref_sq = math.fsum(a * a for a in reference)
    return {"count": len(reference), "different": sum(a != b for a, b in zip(reference, candidate)),
            "relative_l2": math.sqrt(err_sq / ref_sq) if ref_sq else math.sqrt(err_sq),
            "max_abs": max((abs(b - a) for a, b in zip(reference, candidate)), default=0.0)}


def read_gdn_rows(path: Path) -> dict[int, tuple[dict, tuple[float, ...]]]:
    raw = path.read_bytes()
    rows_by_position: dict[int, tuple[dict, tuple[float, ...]]] = {}
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < 12:
            raise ValueError(f"{path}: truncated GDN diagnostic header")
        magic = raw[offset:offset + 8]
        if magic == b"STGDIAG4":
            header_struct = GDN_V4_HEADER
            if len(raw) - offset < header_struct.size:
                raise ValueError(f"{path}: truncated STGDIAG4 header")
            values = header_struct.unpack_from(raw, offset)
            _, version, layer, rows, pos0, n_embd, conv, heads, value_dim, _state, *tokens = values
            positions = tuple(pos0 + i for i in range(rows))
            slots = (-1,) * rows
        elif magic == b"STGDIAG5":
            header_struct = GDN_V5_HEADER
            if len(raw) - offset < header_struct.size:
                raise ValueError(f"{path}: truncated STGDIAG5 header")
            values = header_struct.unpack_from(raw, offset)
            _, version, layer, rows, pos0, n_embd, conv, heads, value_dim, _state, *tail = values
            all_positions, all_slots, all_tokens = tail[:8], tail[8:16], tail[16:24]
            positions = tuple(all_positions[:rows])
            slots = tuple(all_slots[:rows])
            tokens = all_tokens
        else:
            raise ValueError(f"{path}: expected STGDIAG4 or STGDIAG5 at byte {offset}")
        if (version not in (4, 5) or not 1 <= rows <= 8 or n_embd == 0 or
                conv == 0 or heads == 0 or value_dim == 0):
            raise ValueError(f"{path}: invalid GDN diagnostic dimensions")
        record_bytes = rows * (4 * n_embd + 2 * conv + 2 * heads + 2 * value_dim) * 4
        payload_start = offset + header_struct.size
        payload_end = payload_start + record_bytes
        if payload_end > len(raw):
            raise ValueError(f"{path}: truncated GDN diagnostic payload")
        payload = raw[payload_start:payload_end]
        for row, position in enumerate(positions):
            if position in rows_by_position:
                raise ValueError(f"{path}: duplicate GDN row for position {position}")
            x = struct.unpack_from(f"<{n_embd}f", payload, row * n_embd * 4)
            rows_by_position[position] = ({"layer": layer, "position": position,
                "token": tokens[row], "n_embd": n_embd, "slot": slots[row]}, x)
        offset = payload_end
    if not rows_by_position:
        raise ValueError(f"{path}: no GDN diagnostic rows")
    return rows_by_position


def compare(reference: Path, candidate: Path, strata_gdn: Path | None = None,
            ninfer_gdn: Path | None = None) -> dict:
    ref_rows = read_capture_records(reference)
    cand_rows = read_capture_records(candidate)
    if set(ref_rows) != set(cand_rows):
        raise ValueError(f"fused GR-read positions differ: {sorted(ref_rows)} vs {sorted(cand_rows)}")
    positions = sorted(ref_rows)
    per_position = []
    all_fields = sorted(set.intersection(*(set(ref_rows[p][1]) for p in positions)))
    for position in positions:
        ah, a = ref_rows[position]
        bh, b = cand_rows[position]
        if ah != bh:
            raise ValueError(f"capture headers differ at position {position}: {ah} vs {bh}")
        fields = {name: metrics(a[name], b[name]) for name in a}
        first = next((name for name in a if a[name] != b[name]), None)
        per_position.append({"header": ah, "fields": fields, "first_differing_field": first})
    result = {"schema": 1, "header": per_position[0]["header"],
              "fields": {}, "first_differing_field": None}
    for name in all_fields:
        result["fields"][name] = metrics(
            tuple(value for pos in positions for value in ref_rows[pos][1][name]),
            tuple(value for pos in positions for value in cand_rows[pos][1][name]))
    result["first_differing_field"] = next(
        (name for name in all_fields if result["fields"][name]["different"]), None)
    if len(positions) > 1:
        result["positions_compared"] = positions
        result["per_position"] = [dict(position=pos, **row) for pos, row in zip(positions, per_position)]
        result["first_differing_position"] = next(
            (row["position"] for row in result["per_position"] if row["first_differing_field"]), None)
    if (strata_gdn is None) != (ninfer_gdn is None):
        raise ValueError("provide both GDN diagnostic paths or neither")
    if strata_gdn is not None and ninfer_gdn is not None:
        sg_rows = read_gdn_rows(strata_gdn)
        ng_rows = read_gdn_rows(ninfer_gdn)
        common_positions = sorted(set(sg_rows) & set(ng_rows))
        gdn_comparisons = []
        read_links = {}
        for pos in common_positions:
            sh, sx = sg_rows[pos]
            nh, nx = ng_rows[pos]
            if sh["token"] != nh["token"] or sh["n_embd"] != nh["n_embd"] or sh["layer"] != nh["layer"]:
                raise ValueError(f"GDN diagnostic metadata differs at position {pos}")
            gdn_comparisons.append({"position": pos, "token": sh["token"], "x": metrics(sx, nx)})
        for position in positions:
            if position not in sg_rows or position not in ng_rows:
                raise ValueError(f"GDN diagnostics do not contain GR-read position {position}")
            read_header, read_fields = ref_rows[position]
            candidate_header, candidate_fields = cand_rows[position]
            sg_header, sg_x = sg_rows[position]
            ng_header, ng_x = ng_rows[position]
            for label, header in (("Strata", sg_header), ("NInfer", ng_header)):
                for field in ("layer", "position", "token", "n_embd"):
                    if header[field] != read_header[field]:
                        raise ValueError(f"{label} GDN/read {field} mismatch at {position}: {header[field]} vs {read_header[field]}")
            read_links[str(position)] = {
                "strata": metrics(read_fields["mixed"], sg_x),
                "ninfer": metrics(candidate_fields["mixed"], ng_x),
                "cross_backend": metrics(sg_x, ng_x),
            }
        first_read = str(positions[0])
        result["gdn_x_to_gr_mixed"] = {k: v for k, v in read_links[first_read].items() if k != "cross_backend"}
        result["gdn_x_cross_backend"] = read_links[first_read]["cross_backend"]
        result["gdn_x_read_links_by_position"] = read_links
        result["gdn_x_positions_compared"] = gdn_comparisons
        result["first_differing_gdn_x_position"] = next(
            (row["position"] for row in gdn_comparisons if row["x"]["different"]), None)
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
