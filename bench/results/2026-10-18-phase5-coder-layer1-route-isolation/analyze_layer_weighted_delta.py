#!/usr/bin/env python3
"""Reconstruct a layer's combined MoE output delta from matched CPU rows."""
import argparse
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HEADER = struct.Struct("<8sIiiqQQQQQ8i")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, required=True)
parser.add_argument("--layer", type=int, required=True)
parser.add_argument("--left-arm", default="cpu_default")
parser.add_argument("--right-arm", default="cpu_mirror")
parser.add_argument("--position", type=int, default=511)
parser.add_argument("--token-id", type=int, default=271)
parser.add_argument("--output", type=Path)
parser.add_argument("--allow-completion-divergence", action="store_true",
                    help="permit later output IDs to diverge while retaining strict selected-row identity checks")
a = parser.parse_args()
campaign = a.campaign.resolve()
if not 0 <= a.layer < 48 or a.left_arm == a.right_arm:
    parser.error("layer must be in [0, 47] and arms must differ")


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
        if magic != b"STGDIAG4" or version != 4 or layer != a.layer or not 0 < count <= 8 or n != 2560:
            raise ValueError(f"{path}: invalid layer-{a.layer} STGDIAG4 record")
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
    expected = list(range(511, 527))
    if sorted(rows) != expected:
        raise ValueError(f"{path}: expected captured positions {expected}")
    return rows


arms = {}
for arm in (a.left_arm, a.right_arm):
    base = campaign / arm
    result_dir = base / "result"
    route_lines = (result_dir / "device-moe-routes.jsonl").read_text().splitlines()
    if json.loads(route_lines[0]) != {"format": "strata-verify-moe-route-v1", "k": 10}:
        raise ValueError(f"{arm}: unexpected verifier route schema")
    routes = {r["position"]: r for r in map(json.loads, route_lines[1:])}
    if sorted(routes) != list(range(511, 527)) or any(r["layer"] != a.layer for r in routes.values()):
        raise ValueError(f"{arm}: incomplete verifier device route capture")
    host_lines = (result_dir / "routes-all-layers.jsonl").read_text().splitlines()
    host_routes = {(r["layer"], r["position"]): r for r in map(json.loads, host_lines[1:])}
    if len(host_routes) != 768:
        raise ValueError(f"{arm}: incomplete keyed host route capture")
    outputs = {}
    out_path = result_dir / f"cpu-outputs-layer{a.layer}.jsonl"
    for row in map(json.loads, out_path.read_text().splitlines()[1:]):
        key = (row["position"], row["expert"])
        if key in outputs:
            raise ValueError(f"{arm}: duplicate CPU output {key}")
        host = host_routes.get((a.layer, row["position"]))
        if host is None or host["token_id"] != row["token_id"]:
            raise ValueError(f"{arm}: CPU output has no matching host route {key}")
        slot = host["ids"].index(row["expert"])
        if host["route_kind"][slot] >= 0 or host["dispatch"] != row["dispatch"]:
            raise ValueError(f"{arm}: captured output does not belong to a CPU-owned route {key}")
        outputs[key] = tuple(f32(x) for x in row["output"])
    device = read_device(result_dir / "combined-moe.bin")
    request = json.loads((result_dir / "requests.json").read_text())
    supervision = json.loads((base / "supervisor/result.json").read_text())
    samples = [json.loads(x) for x in (base / "supervisor/memory.jsonl").read_text().splitlines()]
    scoped = [cg for sample in samples for cg in sample.get("cgroups", [])
              if cg.get("max_bytes") == 28 * 1024**3]
    events = {key: max((cg.get("memory_events", {}).get(key, 0) for cg in scoped), default=0)
              for key in ("low", "high", "max", "oom", "oom_kill")}
    if (supervision["status"] != "pass" or
            supervision["minimum_available_bytes"] < 6 * 1024**3 or any(events.values())):
        raise ValueError(f"{arm}: supervisor did not pass")
    arms[arm] = {"routes": routes, "host_routes": host_routes, "outputs": outputs,
                 "device": device, "request": request, "supervision": supervision,
                 "memory_samples": len(samples), "memory_events": events}

left, right = arms[a.left_arm], arms[a.right_arm]
if left["request"]["prompt_sha256"] != right["request"]["prompt_sha256"]:
    raise ValueError("prompt hashes differ across arms")
completion_ids_equal = left["request"]["completion_ids"] == right["request"]["completion_ids"]
if not completion_ids_equal and not a.allow_completion_divergence:
    raise ValueError("completion IDs differ across arms")
for arm in (left, right):
    if arm["device"][a.position]["token_id"] != a.token_id:
        raise ValueError("unexpected captured token at selected position")
lroute, rroute = left["routes"][a.position], right["routes"][a.position]
if lroute["token_id"] != a.token_id or rroute["token_id"] != a.token_id:
    raise ValueError("device route/token key mismatch")
if lroute["ids"] != rroute["ids"] or [f32(x) for x in lroute["weights"]] != [f32(x) for x in rroute["weights"]]:
    raise ValueError("device top-k IDs or router weights differ across arms")
if left["device"][a.position]["ffn_x"] != right["device"][a.position]["ffn_x"]:
    raise ValueError("device MoE inputs differ")
lhost = left["host_routes"][(a.layer, a.position)]
rhost = right["host_routes"][(a.layer, a.position)]
if lhost["ids"] != lroute["ids"] or rhost["ids"] != rroute["ids"]:
    raise ValueError("host and device top-k IDs disagree")
if lhost["route_kind"] != rhost["route_kind"]:
    raise ValueError("expert owners differ")
for data, host in ((left, lhost), (right, rhost)):
    if host["token_id"] != a.token_id or tuple(f32(x) for x in host["activation"]) != data["device"][a.position]["ffn_x"]:
        raise ValueError("host route key/input differs from device capture")

cpu_experts = [expert for expert, owner in zip(lroute["ids"], lhost["route_kind"]) if owner < 0]
if not cpu_experts:
    raise ValueError("selected row has no CPU-owned experts")
weighted_delta = [0.0] * 2560
expert_output_changes = []
for expert, weight in zip(lroute["ids"], lroute["weights"]):
    if expert not in cpu_experts:
        continue
    x = left["outputs"].get((a.position, expert))
    y = right["outputs"].get((a.position, expert))
    if x is None or y is None or len(x) != 2560 or len(y) != 2560:
        raise ValueError(f"missing matched CPU output row for expert {expert}")
    diffs = [abs(v - w) for v, w in zip(x, y)]
    expert_output_changes.append({"expert": expert, "different_values": sum(v != w for v, w in zip(x, y)),
                                  "relative_l1": math.fsum(diffs) / max(math.fsum(abs(v) for v in x), 1e-30)})
    for i, (v, w) in enumerate(zip(x, y)):
        weighted_delta[i] += f32(weight) * (v - w)
actual_delta = [x - y for x, y in zip(left["device"][a.position]["ffn_y"], right["device"][a.position]["ffn_y"])]
residual = [x - y for x, y in zip(actual_delta, weighted_delta)]
actual_l1 = math.fsum(abs(x) for x in actual_delta)
relative_residual = math.fsum(abs(x) for x in residual) / max(actual_l1, 1e-30)
result = {
    "schema": 1,
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "quantization": "IQ1_M", "layer": a.layer, "position": a.position, "token_id": a.token_id,
    "arms": [a.left_arm, a.right_arm], "device_input_bitwise_equal": True,
    "completion_ids_equal": completion_ids_equal,
    "completion_id_differences": sum(x != y for x, y in zip(left["request"]["completion_ids"],
                                                               right["request"]["completion_ids"])),
    "device_topk_ids_bitwise_equal": True, "device_router_weights_bitwise_equal": True,
    "owner_vectors_equal": True, "cpu_owned_experts": cpu_experts,
    "cpu_expert_output_deltas": expert_output_changes,
    "supervision": {name: {"samples": arms[name]["memory_samples"],
                    "minimum_host_gib": arms[name]["supervision"]["minimum_available_bytes"] / 2**30,
                    "minimum_admission_gib": arms[name]["supervision"]["minimum_admission_available_bytes"] / 2**30,
                    "memory_events_max": arms[name]["memory_events"]} for name in (a.left_arm, a.right_arm)},
    "weighted_cpu_output_delta_values": len(weighted_delta), "combined_output_delta_values": len(actual_delta),
    "combined_delta_l1": actual_l1, "residual_max_abs": max(map(abs, residual)),
    "residual_l1": math.fsum(abs(x) for x in residual),
    "residual_relative_l1_of_combined_delta": relative_residual,
    "asserted_residual_relative_l1_below_0_0001": relative_residual < 1e-4,
    "scope": "single accepted verifier row; weighted CPU contribution delta compared with device combined MoE delta; float32 combine rounding remains",
}
if not result["asserted_residual_relative_l1_below_0_0001"]:
    raise SystemExit("weighted CPU output delta does not closely reconstruct combined output delta")
out = a.output or (campaign / "analysis-weighted-delta.json")
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
