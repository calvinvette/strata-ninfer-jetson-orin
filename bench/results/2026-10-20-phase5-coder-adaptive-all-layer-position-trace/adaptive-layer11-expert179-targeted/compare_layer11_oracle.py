#!/usr/bin/env python3
"""Join a same-input CPU/GPU expert migration with captured service outputs."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

ROUTE_FORMAT = "strata-moe-dispatch-v3"
PARTS_HEADER = struct.Struct("<8sIIIIQq8i")


def f32(path):
    raw = path.read_bytes()
    if len(raw) % 4:
        raise ValueError(f"{path}: float32 file size is not aligned")
    return raw, struct.unpack(f"<{len(raw) // 4}f", raw)


def summary(a, b):
    if len(a) != len(b):
        raise ValueError("operator output dimensions differ")
    diff = [float(y) - float(x) for x, y in zip(a, b)]
    den = math.fsum(float(x) * float(x) for x in a)
    return {"values": len(a), "different_values": sum(x != y for x, y in zip(a, b)),
            "max_abs_diff": max(map(abs, diff), default=0.0),
            "relative_l2": math.sqrt(math.fsum(x * x for x in diff) / den) if den else None}


def captured_parts(path, layer, position, rank, n_embd=2560):
    data = path.read_bytes()
    offset = 0
    rows = []
    while offset < len(data):
        magic, version, record_layer, count, k, width, pos0, *tokens = PARTS_HEADER.unpack_from(data, offset)
        offset += PARTS_HEADER.size
        if magic != b"STMPART1" or version != 1 or width != n_embd:
            raise ValueError(f"{path}: unsupported parts record")
        size = count * k * width * 4
        values = struct.unpack_from(f"<{count * k * width}f", data, offset)
        offset += size
        if record_layer == layer:
            for row in range(count):
                if pos0 + row == position:
                    start = (row * k + rank) * width
                    rows.append({"token_id": tokens[row], "k": k, "output": values[start:start + width]})
    return rows, hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--operator", type=Path, required=True, help="native_expert_parity dump directory")
    parser.add_argument("--position", type=int, default=511)
    parser.add_argument("--layer", type=int, default=11)
    parser.add_argument("--expert", type=int, default=179)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    arm = args.run / "adaptive-cap8/result"
    records = [json.loads(line) for line in (arm / "all-layer-selected-positions.jsonl").read_text().splitlines()]
    if not records or records[0].get("format") != ROUTE_FORMAT:
        raise ValueError("invalid all-layer dispatch capture")
    route_rows = [row for row in records[1:] if row["layer"] == args.layer and row["position"] == args.position]
    if len(route_rows) != 3:
        raise ValueError(f"expected three short-request routes, got {len(route_rows)}")
    initial_route, recovery_route = route_rows[1], route_rows[2]
    if initial_route["activation"] != recovery_route["activation"]:
        raise ValueError("initial and recovery dispatch inputs differ")
    if initial_route["ids"] != recovery_route["ids"]:
        raise ValueError("initial and recovery expert IDs differ")
    try:
        rank = initial_route["ids"].index(args.expert)
    except ValueError as exc:
        raise ValueError(f"expert {args.expert} is not routed at this layer/position") from exc
    if initial_route["route_kind"][rank] >= 0 or recovery_route["route_kind"][rank] < 0:
        raise ValueError("expected initial CPU ownership and recovery GPU ownership for selected expert")

    captured, parts_hash = captured_parts(arm / "verify-moe-parts.bin", args.layer, args.position, rank)
    if len(captured) != 3 or captured[1]["token_id"] != captured[2]["token_id"]:
        raise ValueError("expected three per-expert output rows")
    route_records = [json.loads(line) for line in (arm / "verify-moe-routes.jsonl").read_text().splitlines()]
    route_matches = [row for row in route_records[1:]
                     if row.get("layer") == args.layer and row.get("position") == args.position]
    if len(route_matches) != 3 or route_matches[1]["token_id"] != route_matches[2]["token_id"]:
        raise ValueError("expected three router rows")
    route_matches = route_matches[1:]
    if route_matches[0]["ids"] != route_matches[1]["ids"] or route_matches[0]["weights"] != route_matches[1]["weights"]:
        raise ValueError("router IDs or weights differ between initial and recovery")
    prefix = f"layer-{args.layer}-expert-{args.expert}"
    activation_dump_raw, activation_dump = f32(args.operator / f"{prefix}-activation.f32")
    route_activation_raw = struct.pack(f"<{len(initial_route['activation'])}f", *initial_route["activation"])
    activation_dump_first = struct.pack("<2560f", *activation_dump[:2560])
    if activation_dump_first != route_activation_raw or len(activation_dump) % 2560 != 0:
        raise ValueError("operator oracle activation does not match the captured service row")
    _, cpu_all = f32(args.operator / f"{prefix}-cpu-output.f32")
    _, gpu_all = f32(args.operator / f"{prefix}-gpu-output.f32")
    _, float_all = f32(args.operator / f"{prefix}-float-output.f32")
    if len(cpu_all) % 2560 or len(gpu_all) % 2560 or len(float_all) % 2560:
        raise ValueError("operator output dump is not a whole number of service rows")
    cpu_output, gpu_output, float_output = cpu_all[:2560], gpu_all[:2560], float_all[:2560]
    if any(len(row["output"]) != 2560 for row in captured):
        raise ValueError("captured expert output width is not 2560")
    result = {
        "scope": "same activation and expert weights, adaptive CPU-to-GPU owner migration, Coder IQ1_M",
        "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
        "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
        "quantization": "IQ1_M",
        "layer": args.layer,
        "position": args.position,
        "token_id": initial_route["token_id"],
        "expert": args.expert,
        "expert_rank": rank,
        "initial_owner_kind": initial_route["route_kind"][rank],
        "recovery_owner_kind": recovery_route["route_kind"][rank],
        "activation_bit_identical": True,
        "router_ids_and_weights_bit_identical": True,
        "native_expert_parity_oracle": {
            "cpu_vs_float_reference": summary(float_output, cpu_output),
            "gpu_vs_float_reference": summary(float_output, gpu_output),
            "cpu_vs_gpu": summary(cpu_output, gpu_output),
        },
        "service_capture_vs_same_input_oracle": {
            "intermediate_cpu_vs_oracle_cpu": summary(cpu_output, captured[1]["output"]),
            "recovery_gpu_vs_oracle_gpu": summary(gpu_output, captured[2]["output"]),
            "service_intermediate_cpu_vs_recovery_gpu": summary(captured[1]["output"], captured[2]["output"]),
        },
        "source_hashes": {
            "all_layer_routes_sha256": hashlib.sha256((arm / "all-layer-selected-positions.jsonl").read_bytes()).hexdigest(),
            "parts_sha256": parts_hash,
            "operator_activation_sha256": hashlib.sha256(route_activation_raw).hexdigest(),
            "operator_activation_dump_sha256": hashlib.sha256(activation_dump_raw).hexdigest(),
        },
        "limitations": ["single selected expert, model position and adaptive pair; no full quality or long-chain drift qualification"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["service_capture_vs_same_input_oracle"], indent=2))


if __name__ == "__main__":
    main()
