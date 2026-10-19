#!/usr/bin/env python3
"""Validate and compare full 16-position Coder route and CPU output captures."""
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/all-16-positions-three-arm-wildcard"
ARMS = ("cpu_default", "cpu_mirror", "gpu_layer1")
HEADER = struct.Struct("<8sIiiqQQQQQ8i")


def vector_delta(a, b):
    diffs = [abs(float(x) - float(y)) for x, y in zip(a, b)]
    return {"exact": list(a) == list(b), "different_values": sum(x != y for x, y in zip(a, b)),
            "max_abs": max(diffs, default=0.0),
            "relative_l1": math.fsum(diffs) / max(math.fsum(abs(float(x)) for x in a), 1e-30)}


def load_device_rows(path):
    data = path.read_bytes()
    offset = 0
    rows = {}
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError(f"{path}: truncated record header")
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STGDIAG4" or version != 4 or layer != 1 or not 0 < count <= 8:
            raise ValueError(f"{path}: unexpected STGDIAG4 header")
        payload_bytes = count * (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        if offset + payload_bytes > len(data):
            raise ValueError(f"{path}: truncated record payload")
        ffn_x_offset = offset + (count * n + 2 * count * c + 2 * count * hv + 2 * count * zv + count * n) * 4
        ffn_y_offset = ffn_x_offset + count * n * 4
        for i in range(count):
            position = pos0 + i
            if position in rows:
                raise ValueError(f"{path}: duplicate device row {position}")
            rows[position] = {
                "token_id": tokens[i],
                "ffn_x": struct.unpack_from(f"<{n}f", data, ffn_x_offset + i * n * 4),
                "ffn_y": struct.unpack_from(f"<{n}f", data, ffn_y_offset + i * n * 4),
            }
        offset += payload_bytes
    return rows


def load_arm(arm):
    path = CAMPAIGN / arm / "result"
    requests = json.loads((path / "requests.json").read_text())
    route_lines = (path / "routes-all-layers.jsonl").read_text().splitlines()
    if json.loads(route_lines[0]).get("format") != "strata-moe-dispatch-v3":
        raise ValueError(f"{arm}: unexpected route schema")
    routes = [json.loads(line) for line in route_lines[1:]]
    l1 = {(row["position"], row["token_id"]): row for row in routes if row["layer"] == 1}
    if len(routes) != 768 or len(l1) != 16:
        raise ValueError(f"{arm}: incomplete route capture: {len(routes)} rows, {len(l1)} layer-1 keys")
    output_lines = (path / "cpu-outputs-layer1.jsonl").read_text().splitlines()
    if json.loads(output_lines[0]).get("format") != "strata-moe-cpu-output-v2":
        raise ValueError(f"{arm}: unexpected CPU output schema")
    outputs = {}
    for line in output_lines[1:]:
        row = json.loads(line)
        key = (row["position"], row["token_id"], row["expert"])
        if row["layer"] != 1 or key in outputs:
            raise ValueError(f"{arm}: invalid or duplicate CPU output key {key}")
        route = l1.get(key[:2])
        if route is None or row["expert"] not in route["ids"]:
            raise ValueError(f"{arm}: CPU output has no matching route key {key}")
        slot = route["ids"].index(row["expert"])
        if route["route_kind"][slot] >= 0:
            raise ValueError(f"{arm}: captured CPU output is not CPU-owned in route {key}")
        if row["dispatch"] != route["dispatch"]:
            raise ValueError(f"{arm}: output/route dispatch mismatch {key}")
        outputs[key] = row["output"]
    devices = load_device_rows(path / "combined-moe.bin")
    supervisor = json.loads((CAMPAIGN / arm / "supervisor/result.json").read_text())
    samples = [json.loads(line) for line in (CAMPAIGN / arm / "supervisor/memory.jsonl").read_text().splitlines()]
    scope_samples = [cg for sample in samples for cg in sample.get("cgroups", [])
                     if cg.get("max_bytes") == 28 * 1024**3]
    event_max = {key: max((cg.get("memory_events", {}).get(key, 0) for cg in scope_samples), default=0)
                 for key in ("high", "max", "oom", "oom_kill")}
    scope_peak = max((cg.get("current_bytes", 0) for cg in scope_samples), default=0)
    return {"requests": requests, "routes": l1, "outputs": outputs, "device": devices,
            "memory": supervisor, "memory_events": event_max, "scope_peak": scope_peak}


arms = {arm: load_arm(arm) for arm in ARMS}
if any(arms[arm]["memory"]["status"] != "pass" for arm in ARMS):
    raise SystemExit("one or more supervised arms failed")
if any(value != 0 for arm in ARMS for value in arms[arm]["memory_events"].values()):
    raise SystemExit("one or more supervisor cgroup memory counters are nonzero")
if len({a["requests"]["prompt_sha256"] for a in arms.values()}) != 1:
    raise SystemExit("prompt hashes differ across arms")
if len({tuple(a["requests"]["completion_ids"]) for a in arms.values()}) != 1:
    raise SystemExit("completion token IDs differ across arms")

row_summaries = []
for key in sorted(arms["cpu_default"]["routes"]):
    d, m, g = (arms[arm]["routes"][key] for arm in ARMS)
    pos, token = key
    device = {arm: arms[arm]["device"].get(pos) for arm in ARMS}
    if any(row is None or row["token_id"] != token for row in device.values()):
        raise ValueError(f"device trace missing or mismatched token at {key}")
    output_deltas = {}
    common_cpu = sorted(set(arms["cpu_default"]["outputs"]) & set(arms["cpu_mirror"]["outputs"]))
    common_cpu = [k for k in common_cpu if k[:2] == key]
    for output_key in common_cpu:
        output_deltas[str(output_key[2])] = vector_delta(
            arms["cpu_default"]["outputs"][output_key], arms["cpu_mirror"]["outputs"][output_key])
    device_cpu_common = sorted(set(arms["cpu_default"]["outputs"]) & set(arms["gpu_layer1"]["outputs"]))
    device_cpu_common = [k for k in device_cpu_common if k[:2] == key]
    default_gpu_cpu_deltas = {str(k[2]): vector_delta(arms["cpu_default"]["outputs"][k],
                                                       arms["gpu_layer1"]["outputs"][k])
                              for k in device_cpu_common}
    row_summaries.append({
        "position": pos, "token_id": token,
        "expert_ids_equal": d["ids"] == m["ids"] == g["ids"],
        "cpu_owners": {arm: [expert for expert, owner in zip(arms[arm]["routes"][key]["ids"],
                                                              arms[arm]["routes"][key]["route_kind"])
                              if owner < 0] for arm in ARMS},
        "route_activation_cpu_default_mirror_equal": d["activation"] == m["activation"],
        "route_activation_mirror_gpu": vector_delta(m["activation"], g["activation"]),
        "route_activation_vs_device_ffn_x": {arm: vector_delta(arms[arm]["routes"][key]["activation"],
                                                                 device[arm]["ffn_x"]) for arm in ARMS},
        "host_capture_matches_device_within_1e-7": {arm: vector_delta(
            arms[arm]["routes"][key]["activation"], device[arm]["ffn_x"])["max_abs"] <= 1e-7
            for arm in ARMS},
        "device_ffn_x_default_mirror": vector_delta(device["cpu_default"]["ffn_x"], device["cpu_mirror"]["ffn_x"]),
        "device_ffn_x_mirror_gpu": vector_delta(device["cpu_mirror"]["ffn_x"], device["gpu_layer1"]["ffn_x"]),
        "device_combined_ffn_y_default_mirror": vector_delta(device["cpu_default"]["ffn_y"], device["cpu_mirror"]["ffn_y"]),
        "device_combined_ffn_y_mirror_gpu": vector_delta(device["cpu_mirror"]["ffn_y"], device["gpu_layer1"]["ffn_y"]),
        "default_vs_q8_1_cpu_expert_outputs": output_deltas,
        "default_cpu_vs_gpu_profile_cpu_outputs": default_gpu_cpu_deltas,
    })

default_vs_mirror = [value for row in row_summaries
                     for value in row["default_vs_q8_1_cpu_expert_outputs"].values()]
default_vs_gpu = [value for row in row_summaries
                  for value in row["default_cpu_vs_gpu_profile_cpu_outputs"].values()]
default_mirror_l1 = sorted(value["relative_l1"] for value in default_vs_mirror)
states = {arm: arms[arm]["requests"]["state"] for arm in ARMS}
state_fields = sorted(set().union(*(set(value) for value in states.values())))
def quantile(values, q):
    index = (len(values) - 1) * q
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)

out = {
    "schema": 1,
    "campaign": str(CAMPAIGN.relative_to(ROOT)),
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "model_quantization": "IQ1_M",
    "arms": {arm: {
        "prompt_sha256": arms[arm]["requests"]["prompt_sha256"],
        "completion_ids": arms[arm]["requests"]["completion_ids"],
        "route_rows": 768, "layer1_positions": 16,
        "cpu_output_rows": len(arms[arm]["outputs"]),
        "minimum_host_available_bytes": arms[arm]["memory"]["minimum_available_bytes"],
        "minimum_admission_available_bytes": arms[arm]["memory"]["minimum_admission_available_bytes"],
        "cgroup_28g_peak_bytes": arms[arm]["scope_peak"],
        "cgroup_memory_events_max": arms[arm]["memory_events"],
        "supervisor_status": arms[arm]["memory"]["status"],
    } for arm in ARMS},
    "summary": {
        "device_ffn_x_all_arms_bitwise_equal": all(
            row["device_ffn_x_default_mirror"]["exact"] and row["device_ffn_x_mirror_gpu"]["exact"]
            for row in row_summaries),
        "route_host_capture_within_1e-7_of_device_ffn_x": {
            arm: sum(row["host_capture_matches_device_within_1e-7"][arm] for row in row_summaries)
            for arm in ARMS},
        "cpu_default_and_mirror_inputs_bitwise_equal": all(
            row["route_activation_cpu_default_mirror_equal"] for row in row_summaries),
        "cpu_default_vs_q8_1_shared_cpu_output_rows": sum(
            len(row["default_vs_q8_1_cpu_expert_outputs"]) for row in row_summaries),
        "cpu_default_vs_q8_1_different_rows": sum(
            not item["exact"] for row in row_summaries
            for item in row["default_vs_q8_1_cpu_expert_outputs"].values()),
        "cpu_default_vs_q8_1_output_relative_l1_min_median_max": [
            min(default_mirror_l1), quantile(default_mirror_l1, 0.5), max(default_mirror_l1)],
        "cpu_default_vs_q8_1_output_max_abs_max": max(item["max_abs"] for item in default_vs_mirror),
        "cpu_default_vs_gpu_profile_shared_cpu_output_rows": sum(
            len(row["default_cpu_vs_gpu_profile_cpu_outputs"]) for row in row_summaries),
        "cpu_default_vs_gpu_profile_shared_cpu_output_rows_equal": sum(
            item["exact"] for row in row_summaries
            for item in row["default_cpu_vs_gpu_profile_cpu_outputs"].values()),
        "cpu_default_vs_gpu_profile_shared_cpu_output_rows_different": sum(
            not item["exact"] for item in default_vs_gpu),
        "gpu_profile_changed_cpu_owner_positions": [row["position"] for row in row_summaries
            if row["cpu_owners"]["cpu_mirror"] != row["cpu_owners"]["gpu_layer1"]],
        "gpu_profile_cpu_owner_rows_moved": sum(
            len(row["cpu_owners"]["cpu_mirror"]) - len(row["cpu_owners"]["gpu_layer1"])
            for row in row_summaries),
        "device_ffn_y_default_mirror_different_positions": [row["position"] for row in row_summaries
            if not row["device_combined_ffn_y_default_mirror"]["exact"]],
        "device_ffn_y_mirror_gpu_equal_positions": [row["position"] for row in row_summaries
            if row["device_combined_ffn_y_mirror_gpu"]["exact"]],
        "device_ffn_y_mirror_gpu_different_positions": [row["position"] for row in row_summaries
            if not row["device_combined_ffn_y_mirror_gpu"]["exact"]],
        "persistent_state_equal_across_arms": len({json.dumps(state, sort_keys=True) for state in states.values()}) == 1,
        "persistent_state_changed_fields": {f"{a}_vs_{b}": [key for key in state_fields
            if states[a].get(key) != states[b].get(key)]
            for a, b in (("cpu_default", "cpu_mirror"), ("cpu_mirror", "gpu_layer1"))},
    },
    "rows": row_summaries,
}
(CAMPAIGN / "analysis-all16.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"positions": len(row_summaries),
                  **out["summary"],
                  "analysis": str(CAMPAIGN / "analysis-all16.json")}, indent=2))
