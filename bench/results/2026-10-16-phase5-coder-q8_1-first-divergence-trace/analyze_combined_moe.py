#!/usr/bin/env python3
"""Compare actual verifier layer-1 weighted-combine outputs from paired services."""
import argparse
import json
import math
import struct
from pathlib import Path

HEADER = struct.Struct("<8sIiiqQQQQQ8i")


def read_combined(path):
    data = Path(path).read_bytes()
    offset = 0
    records = []
    layer_seen = None
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError("truncated GDN diagnostic header")
        magic, version, layer, rows, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STGDIAG4" or version != 4 or not 0 < rows <= 8:
            raise ValueError(f"expected STGDIAG4 at byte {offset - HEADER.size}")
        if layer_seen is not None and layer_seen != layer:
            raise ValueError("capture contains more than one layer")
        layer_seen = layer
        base_counts = (rows * n, rows * c, rows * c, rows * hv, rows * hv, rows * zv, rows * zv)
        ffn_y_offset = offset + (sum(base_counts) + 2 * rows * n) * 4
        payload_bytes = (sum(base_counts) + 3 * rows * n) * 4
        if offset + payload_bytes > len(data):
            raise ValueError("truncated GDN diagnostic payload")
        for row in range(rows):
            values = struct.unpack_from(f"<{n}f", data, ffn_y_offset + row * n * 4)
            records.append({"position": pos0 + row, "token": tokens[row], "ffn_y": values})
        offset += payload_bytes
    return layer_seen, records


def read_jsonl(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    return rows[1:]


def compare_route_traces(default_dir, mirror_dir):
    default = read_jsonl(default_dir / "layer1.jsonl")
    mirror = read_jsonl(mirror_dir / "layer1.jsonl")
    if len(default) != len(mirror):
        raise ValueError("paired route traces have different row counts")
    counts = {"rows": len(default), "key_mismatches": 0,
              "activation_mismatches": 0, "expert_id_mismatches": 0,
              "owner_mismatches": 0}
    first = {}
    for index, (a, b) in enumerate(zip(default, mirror)):
        key = (a.get("dispatch"), a.get("layer"), a.get("row"))
        other = (b.get("dispatch"), b.get("layer"), b.get("row"))
        if key != other:
            counts["key_mismatches"] += 1
            continue
        for field, name in (("activation", "activation_mismatches"),
                            ("ids", "expert_id_mismatches"),
                            ("route_kind", "owner_mismatches")):
            if a[field] != b[field]:
                counts[name] += 1
                if name not in first:
                    first[name] = {"row": index, "dispatch": key[0], "layer": key[1]}
    return {"counts": counts, "first_mismatch": first}


def route_and_cpu_comparison(default_dir, mirror_dir):
    default_trace = read_jsonl(default_dir / "layer1.jsonl")
    mirror_trace = read_jsonl(mirror_dir / "layer1.jsonl")
    a = next(row for row in default_trace if row["dispatch"] == 1393 and row["layer"] == 1)
    b = next(row for row in mirror_trace if row["dispatch"] == 1393 and row["layer"] == 1)
    route = {"dispatch": 1393, "layer": 1,
             "activation_bitwise_equal": a["activation"] == b["activation"],
             "expert_ids_equal": a["ids"] == b["ids"], "owners_equal": a["route_kind"] == b["route_kind"],
             "expert_ids": a["ids"], "route_kind": a["route_kind"], "n_tok": a["n_tok"], "k": a["k"]}
    default_cpu = {row["expert"]: row["output"] for row in read_jsonl(default_dir / "cpu-outputs.jsonl")
                   if row["dispatch"] == 1393}
    mirror_cpu = {row["expert"]: row["output"] for row in read_jsonl(mirror_dir / "cpu-outputs.jsonl")
                  if row["dispatch"] == 1393}
    if default_cpu.keys() != mirror_cpu.keys():
        raise ValueError("CPU-owned expert rows differ between the paired dispatches")
    cpu_deltas = []
    for expert in sorted(default_cpu):
        x, y = default_cpu[expert], mirror_cpu[expert]
        delta = [float(u) - float(v) for u, v in zip(x, y)]
        cpu_deltas.append({"expert": expert, "different_values": sum(u != v for u, v in zip(x, y)),
                           "elements": len(x), "relative_l1": math.fsum(abs(v) for v in delta) /
                           max(math.fsum(abs(float(v)) for v in x), 1e-30)})
    return {"route_pair": route, "cpu_output_deltas": cpu_deltas}


def service_outcomes(default_dir, mirror_dir):
    a = json.loads((default_dir / "analysis.json").read_text())
    b = json.loads((mirror_dir / "analysis.json").read_text())
    rows = []
    for left, right in zip(a["requests"], b["requests"]):
        rows.append({"name": left["name"], "default_tokens": len(left["ids"]), "mirror_tokens": len(right["ids"]),
                     "different_token_positions": sum(x != y for x, y in zip(left["ids"], right["ids"])) +
                     abs(len(left["ids"]) - len(right["ids"])),
                     "persistent_state_equal": left["state"] == right["state"]})
    return rows


def supervision(default_dir, mirror_dir):
    summary = {}
    for label, directory in (("default", default_dir), ("cuda_mirror", mirror_dir)):
        result = json.loads((directory.parent / "supervisor" / "result.json").read_text())
        samples = [json.loads(line) for line in (directory.parent / "supervisor" / "memory.jsonl").read_text().splitlines()]
        events = {"low": 0, "high": 0, "max": 0, "oom": 0, "oom_kill": 0}
        for sample in samples:
            for cgroup in sample.get("cgroups", []):
                for key in events:
                    events[key] = max(events[key], int(cgroup.get("memory_events", {}).get(key, 0)))
        summary[label] = {"status": result.get("status"), "memory_samples": len(samples),
                          "minimum_host_available_gib": result.get("minimum_available_bytes", 0) / 2**30,
                          "minimum_admission_available_gib": result.get("minimum_admission_available_bytes", 0) / 2**30,
                          "maximum_cgroup_memory_events": events}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("default", type=Path)
    parser.add_argument("mirror", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--default-service", type=Path)
    parser.add_argument("--mirror-service", type=Path)
    args = parser.parse_args()
    layer_a, default = read_combined(args.default)
    layer_b, mirror = read_combined(args.mirror)
    if layer_a != 1 or layer_b != 1:
        raise SystemExit(f"expected layer 1 captures, got {layer_a} and {layer_b}")

    compared = 0
    mismatched_input = []
    first = None
    exact_outputs = 0
    for index, (a, b) in enumerate(zip(default, mirror)):
        key_a, key_b = (a["position"], a["token"]), (b["position"], b["token"])
        if key_a != key_b:
            mismatched_input.append({"row": index, "default": key_a, "mirror": key_b})
            continue
        ya, yb = a["ffn_y"], b["ffn_y"]
        compared += 1
        different = sum(x != y for x, y in zip(ya, yb))
        if different == 0:
            exact_outputs += 1
            continue
        if first is None:
            delta = [float(x) - float(y) for x, y in zip(ya, yb)]
            first = {"row": index, "position": a["position"], "token": a["token"],
                     "different_values": different,
                     "elements": len(ya), "max_abs": max(abs(value) for value in delta),
                     "relative_l1": math.fsum(abs(value) for value in delta) /
                                    max(math.fsum(abs(float(value)) for value in ya), 1e-30)}

    report = {
        "model": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "layer": 1,
        "capture": "STGDIAG4 ffn_y, after expert weighted combine plus shared expert",
        "default_rows": len(default), "mirror_rows": len(mirror),
        "position_token_matched_rows": compared, "exact_combined_output_rows": exact_outputs,
        "mismatched_input_rows": len(mismatched_input),
        "first_mismatched_position_token": mismatched_input[0] if mismatched_input else None,
        "first_combined_output_difference": first,
    }
    if args.default_service and args.mirror_service:
        report["route_trace_comparison"] = compare_route_traces(args.default_service, args.mirror_service)
        report["actual_service_route_and_cpu_rows"] = route_and_cpu_comparison(args.default_service,
                                                                                args.mirror_service)
        report["request_outcomes"] = service_outcomes(args.default_service, args.mirror_service)
        report["supervision"] = supervision(args.default_service, args.mirror_service)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
