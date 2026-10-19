#!/usr/bin/env python3
"""Check whether exact verifier route weights explain layer-8 combined-output delta."""
import json
import argparse
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/layer8-weighted-output-pair-final"
HEADER = struct.Struct("<8sIiiqQQQQQ8i")
ARMS = ("cpu_mirror", "gpu_layer1")
POSITION = 511
TOKEN_ID = 271
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
CAMPAIGN = parser.parse_args().campaign.resolve()


def f32(value):
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def read_device(path):
    data = path.read_bytes()
    offset = 0
    rows = {}
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError(f"{path}: truncated diagnostic header")
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STGDIAG4" or version != 4 or layer != 8 or not 0 < count <= 8 or n != 2560:
            raise ValueError(f"{path}: invalid layer-8 STGDIAG4 record")
        payload = count * (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        if offset + payload > len(data):
            raise ValueError(f"{path}: truncated layer data")
        x_at = offset + (2 * count * n + 2 * count * c + 2 * count * hv + 2 * count * zv) * 4
        y_at = x_at + count * n * 4
        for i in range(count):
            rows[pos0 + i] = {"token_id": tokens[i],
                              "ffn_x": struct.unpack_from(f"<{n}f", data, x_at + i * n * 4),
                              "ffn_y": struct.unpack_from(f"<{n}f", data, y_at + i * n * 4)}
        offset += payload
    if sorted(rows) != list(range(511, 527)):
        raise ValueError(f"{path}: expected positions 511–526")
    return rows


arms = {}
for arm in ARMS:
    base = CAMPAIGN / arm
    result_dir = base / "result"
    route_path = result_dir / "device-moe-routes.jsonl"
    route_lines = route_path.read_text().splitlines()
    header = json.loads(route_lines[0])
    if header != {"format": "strata-verify-moe-route-v1", "k": 10}:
        raise ValueError(f"{arm}: unexpected verifier route schema")
    routes = {r["position"]: r for r in map(json.loads, route_lines[1:])}
    if sorted(routes) != list(range(511, 527)) or any(r["layer"] != 8 for r in routes.values()):
        raise ValueError(f"{arm}: incomplete verifier device route capture")
    host_lines = (result_dir / "routes-all-layers.jsonl").read_text().splitlines()
    host_rows = [json.loads(x) for x in host_lines[1:]]
    host_routes = {(r["layer"], r["position"]): r for r in host_rows}
    if len(host_routes) != 768:
        raise ValueError(f"{arm}: incomplete keyed host route capture")
    outputs = {}
    out_lines = (result_dir / "cpu-outputs-layer8.jsonl").read_text().splitlines()
    for row in map(json.loads, out_lines[1:]):
        key = (row["position"], row["expert"])
        if key in outputs:
            raise ValueError(f"{arm}: duplicate CPU output {key}")
        host_route = host_routes.get((8, row["position"]))
        if host_route is None or host_route["token_id"] != row["token_id"]:
            raise ValueError(f"{arm}: CPU output has no matching host route {key}")
        slot = host_route["ids"].index(row["expert"])
        if host_route["route_kind"][slot] >= 0 or host_route["dispatch"] != row["dispatch"]:
            raise ValueError(f"{arm}: captured output does not belong to a CPU-owned route {key}")
        outputs[key] = tuple(f32(x) for x in row["output"])
    device = read_device(result_dir / "combined-moe.bin")
    request = json.loads((result_dir / "requests.json").read_text())
    supervision = json.loads((base / "supervisor/result.json").read_text())
    samples = [json.loads(x) for x in (base / "supervisor/memory.jsonl").read_text().splitlines()]
    scoped = [cg for sample in samples for cg in sample.get("cgroups", [])
              if cg.get("max_bytes") == 28 * 1024**3]
    events = {key: max((cg.get("memory_events", {}).get(key, 0) for cg in scoped), default=0)
              for key in ("high", "max", "oom", "oom_kill")}
    if (supervision["status"] != "pass" or
            supervision["minimum_available_bytes"] < 6 * 1024**3 or any(events.values())):
        raise ValueError(f"{arm}: supervisor did not pass")
    arms[arm] = {"routes": routes, "host_routes": host_routes, "outputs": outputs,
                 "device": device, "request": request, "supervision": supervision,
                 "memory_samples": len(samples), "memory_events": events}

left, right = (arms[a] for a in ARMS)
if left["request"]["prompt_sha256"] != right["request"]["prompt_sha256"]:
    raise ValueError("prompt hashes differ across arms")
if left["request"]["completion_ids"] != right["request"]["completion_ids"]:
    raise ValueError("completion IDs differ across arms")
if left["device"][POSITION]["token_id"] != TOKEN_ID or right["device"][POSITION]["token_id"] != TOKEN_ID:
    raise ValueError("unexpected position-511 token")
lroute, rroute = left["routes"][POSITION], right["routes"][POSITION]
if lroute["token_id"] != TOKEN_ID or rroute["token_id"] != TOKEN_ID:
    raise ValueError("device route/token key mismatch")
if lroute["ids"] != rroute["ids"] or [f32(x) for x in lroute["weights"]] != [f32(x) for x in rroute["weights"]]:
    raise ValueError("position-511 device top-k IDs or weights differ across arms")
if left["device"][POSITION]["ffn_x"] != right["device"][POSITION]["ffn_x"]:
    raise ValueError("position-511 device MoE inputs differ")
lhost = left["host_routes"][(8, POSITION)]
rhost = right["host_routes"][(8, POSITION)]
if lhost["ids"] != lroute["ids"] or rhost["ids"] != rroute["ids"]:
    raise ValueError("host and device top-k IDs disagree")
if lhost["route_kind"] != rhost["route_kind"]:
    raise ValueError("position-511 expert owners differ")
if lhost["token_id"] != TOKEN_ID or rhost["token_id"] != TOKEN_ID:
    raise ValueError("host route/token key mismatch")
for arm_data in (left, right):
    host = arm_data["host_routes"][(8, POSITION)]
    if tuple(f32(x) for x in host["activation"]) != arm_data["device"][POSITION]["ffn_x"]:
        raise ValueError("host route input differs from device-captured ffn_x")

cpu_experts = [e for e, owner in zip(lroute["ids"], lhost["route_kind"]) if owner < 0]
if len(cpu_experts) != 7:
    raise ValueError(f"expected seven CPU owners, found {cpu_experts}")
weighted_delta = [0.0] * 2560
expert_output_changes = []
for expert, weight in zip(lroute["ids"], lroute["weights"]):
    if expert not in cpu_experts:
        continue
    a = left["outputs"].get((POSITION, expert))
    b = right["outputs"].get((POSITION, expert))
    if a is None or b is None or len(a) != 2560 or len(b) != 2560:
        raise ValueError(f"missing matched CPU output row for expert {expert}")
    expert_diffs = [abs(x - y) for x, y in zip(a, b)]
    expert_output_changes.append({
        "expert": expert,
        "different_values": sum(x != y for x, y in zip(a, b)),
        "relative_l1": math.fsum(expert_diffs) / max(math.fsum(abs(x) for x in a), 1e-30),
    })
    w = f32(weight)
    for i, (x, y) in enumerate(zip(a, b)):
        weighted_delta[i] += w * (x - y)
actual_delta = [x - y for x, y in zip(left["device"][POSITION]["ffn_y"],
                                     right["device"][POSITION]["ffn_y"])]
residual = [x - y for x, y in zip(actual_delta, weighted_delta)]
actual_l1 = math.fsum(abs(x) for x in actual_delta)
result = {
    "schema": 1,
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "quantization": "IQ1_M",
    "position": POSITION,
    "token_id": TOKEN_ID,
    "arms": list(ARMS),
    "device_input_bitwise_equal": True,
    "device_topk_ids_bitwise_equal": True,
    "device_router_weights_bitwise_equal": True,
    "owner_vectors_equal": True,
    "cpu_owned_experts": cpu_experts,
    "cpu_expert_output_deltas": expert_output_changes,
    "supervision": {arm: {
        "samples": arms[arm]["memory_samples"],
        "minimum_host_gib": arms[arm]["supervision"]["minimum_available_bytes"] / 2**30,
        "minimum_admission_gib": arms[arm]["supervision"]["minimum_admission_available_bytes"] / 2**30,
        "memory_events_max": arms[arm]["memory_events"],
    } for arm in ARMS},
    "weighted_cpu_output_delta_values": len(weighted_delta),
    "combined_output_delta_values": len(actual_delta),
    "combined_delta_l1": actual_l1,
    "residual_max_abs": max(map(abs, residual)),
    "residual_l1": math.fsum(abs(x) for x in residual),
    "residual_relative_l1_of_combined_delta": math.fsum(abs(x) for x in residual) / max(actual_l1, 1e-30),
    "asserted_residual_relative_l1_below_0_0001": math.fsum(abs(x) for x in residual) / max(actual_l1, 1e-30) < 1e-4,
    "scope": "single accepted verifier row; weighted CPU contribution delta compared with device combined MoE delta; float32 combine rounding remains",
}
if not result["asserted_residual_relative_l1_below_0_0001"]:
    raise SystemExit("weighted CPU output delta does not closely reconstruct combined output delta")
out = CAMPAIGN / "analysis-weighted-delta.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
