#!/usr/bin/env python3
"""Cross-check direct CPU-owner captures against the service verifier parts buffer."""
import argparse
import json
import math
from pathlib import Path
import struct


HEADER = struct.Struct("<8sIIIIQq8i")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def read_parts(path):
    data = path.read_bytes()
    offset = 0
    rows = []
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError("truncated verifier-parts header")
        magic, version, layer, n_rows, k, width, pos0, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STMPART1" or version != 1 or width <= 0 or n_rows > len(tokens):
            raise ValueError("unexpected verifier-parts header")
        count = n_rows * k * width
        size = count * 4
        if offset + size > len(data):
            raise ValueError("truncated verifier-parts payload")
        values = struct.unpack_from(f"<{count}f", data, offset)
        offset += size
        for token_row in range(n_rows):
            expert_rows = [
                values[(token_row * k + expert_rank) * width:(token_row * k + expert_rank + 1) * width]
                for expert_rank in range(k)
            ]
            rows.append({
                "layer": layer,
                "position": pos0 + token_row,
                "token_id": tokens[token_row],
                "expert_rows": expert_rows,
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result
    route_trace = [row for row in read_jsonl(root / "all-layer-selected-positions.jsonl")[1:]
                   if row.get("layer") == 40 and row.get("position") == 512]
    verifier_routes = [row for row in read_jsonl(root / "verify-moe-routes.jsonl")[1:]
                       if row.get("layer") == 40 and row.get("position") == 512]
    parts = [row for row in read_parts(root / "verify-moe-parts.bin")
             if row["layer"] == 40 and row["position"] == 512]
    cpu_outputs = [row for row in read_jsonl(root / "cpu-moe-outputs.jsonl")[1:]
                   if row.get("layer") == 40 and row.get("position") == 512]
    if not (len(route_trace) == len(verifier_routes) == len(parts) == 3):
        raise ValueError("expected three ordered short-request records in route and parts captures")

    aligned = []
    for dispatch_row, verifier_row, parts_row in zip(route_trace, verifier_routes, parts):
        if (dispatch_row["token_id"] != verifier_row["token_id"] or
                dispatch_row["ids"] != verifier_row["ids"] or
                dispatch_row["token_id"] != parts_row["token_id"]):
            raise ValueError("route and verifier-parts records do not align in request order")
        if len(parts_row["expert_rows"]) != len(verifier_row["ids"]):
            raise ValueError("verifier-parts expert width differs from route record")
        aligned.append({"dispatch_id": dispatch_row["dispatch"], "dispatch": dispatch_row,
                        "route": verifier_row, "parts": parts_row})

    comparisons = []
    for cpu_row in cpu_outputs:
        matches = [item for item in aligned
                   if item["dispatch_id"] == cpu_row["dispatch"] and
                   item["parts"]["token_id"] == cpu_row["token_id"]]
        if len(matches) != 1:
            raise ValueError("direct CPU output could not be uniquely joined to its verifier-parts record")
        item = matches[0]
        route = item["route"]
        if cpu_row["expert"] not in route["ids"]:
            raise ValueError("captured CPU expert is absent from the joined route")
        rank = route["ids"].index(cpu_row["expert"])
        if item["dispatch"]["route_kind"][rank] >= 0:
            raise ValueError("direct CPU output row is not marked CPU-owned in route trace")
        direct = cpu_row["output"]
        mixed = item["parts"]["expert_rows"][rank]
        if len(direct) != len(mixed):
            raise ValueError("direct CPU row and verifier-parts row have different widths")
        diffs = [abs(a - b) for a, b in zip(direct, mixed)]
        comparisons.append({
            "dispatch": cpu_row["dispatch"],
            "layer": cpu_row["layer"],
            "position": cpu_row["position"],
            "token_id": cpu_row["token_id"],
            "expert": cpu_row["expert"],
            "route_rank": rank,
            "different_serialized_values": sum(a != b for a, b in zip(direct, mixed)),
            "max_abs_difference": max(diffs, default=0.0),
            "relative_l2_difference": math.sqrt(sum(d * d for d in diffs)) /
                max(math.sqrt(sum(x * x for x in mixed)), 1e-300),
            "note": "CPU JSONL uses 9 significant digits; verifier-parts stores FP32 bytes.",
        })
    result = {
        "scope": "direct CPU pool outputs versus the same service verifier's assembled per-expert parts",
        "model_identity": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "layer": 40,
        "position": 512,
        "ordered_short_request_dispatches": [row["dispatch"] for row in route_trace],
        "parts_capture_semantics": (
            "Verifier copies parts_out after CPU rows are copied from the mapped pool buffer and GPU hit rows are added; "
            "these are the actual mixed-owner service parts consumed by MoE combine."
        ),
        "cpu_rows_checked": len(comparisons),
        "comparisons": comparisons,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "cpu_rows_checked": len(comparisons),
                      "max_abs_difference": max(row["max_abs_difference"] for row in comparisons)}, indent=2))


if __name__ == "__main__":
    main()
