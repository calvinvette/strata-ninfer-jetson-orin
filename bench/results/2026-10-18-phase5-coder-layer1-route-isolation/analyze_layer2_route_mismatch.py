#!/usr/bin/env python3
"""Summarize an upstream device-input/router change for the layer-2 pair."""
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "bench/results/2026-10-19-phase5-coder-layer2-weighted-output-pair"
HEADER = struct.Struct("<8sIiiqQQQQQ8i")
ARMS = ("cpu_default", "cpu_mirror")
POSITION = 511
TOKEN_ID = 271


def read_device(path):
    data = path.read_bytes()
    offset = 0
    rows = {}
    while offset < len(data):
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STGDIAG4" or version != 4 or layer != 2 or not 0 < count <= 8 or n != 2560:
            raise ValueError(f"invalid layer-2 device record in {path}")
        payload = count * (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        x_at = offset + (2 * count * n + 2 * count * c + 2 * count * hv + 2 * count * zv) * 4
        y_at = x_at + count * n * 4
        for i in range(count):
            rows[pos0 + i] = {
                "token_id": tokens[i],
                "ffn_x": struct.unpack_from(f"<{n}f", data, x_at + i * n * 4),
                "ffn_y": struct.unpack_from(f"<{n}f", data, y_at + i * n * 4),
            }
        offset += payload
    if sorted(rows) != list(range(511, 527)):
        raise ValueError("incomplete device capture")
    return rows


arms = {}
for name in ARMS:
    base = CAMPAIGN / name
    result = base / "result"
    route_lines = (result / "device-moe-routes.jsonl").read_text().splitlines()
    if json.loads(route_lines[0]) != {"format": "strata-verify-moe-route-v1", "k": 10}:
        raise ValueError("unexpected route capture schema")
    route_rows = [json.loads(line) for line in route_lines[1:]]
    if len(route_rows) != 16 or any(row["layer"] != 2 for row in route_rows):
        raise ValueError("incomplete layer-2 route capture")
    request = json.loads((result / "requests.json").read_text())
    supervisor = json.loads((base / "supervisor/result.json").read_text())
    if supervisor["status"] != "pass" or supervisor["minimum_available_bytes"] < 6 * 1024**3:
        raise ValueError(f"{name}: supervisor failed its memory guard")
    samples = [json.loads(line) for line in (base / "supervisor/memory.jsonl").read_text().splitlines()]
    scoped = [cg for sample in samples for cg in sample.get("cgroups", [])
              if cg.get("max_bytes") == 28 * 1024**3]
    events = {key: max((cg.get("memory_events", {}).get(key, 0) for cg in scoped), default=0)
              for key in ("low", "high", "max", "oom", "oom_kill")}
    if any(events.values()):
        raise ValueError(f"{name}: observed cgroup memory events {events}")
    arms[name] = {"route": {row["position"]: row for row in route_rows},
                  "device": read_device(result / "combined-moe.bin"),
                  "request": request, "supervisor": supervisor, "memory_events": events}

left, right = (arms[name] for name in ARMS)
if left["request"]["prompt_sha256"] != right["request"]["prompt_sha256"]:
    raise ValueError("prompt differs")
if left["request"]["completion_ids"] != right["request"]["completion_ids"]:
    raise ValueError("completion differs")
lp, rp = left["device"][POSITION], right["device"][POSITION]
lr, rr = left["route"][POSITION], right["route"][POSITION]
if lp["token_id"] != TOKEN_ID or rp["token_id"] != TOKEN_ID or lr["token_id"] != TOKEN_ID or rr["token_id"] != TOKEN_ID:
    raise ValueError("unexpected position/token key")
weights_l = [struct.unpack("<f", struct.pack("<f", x))[0] for x in lr["weights"]]
weights_r = [struct.unpack("<f", struct.pack("<f", x))[0] for x in rr["weights"]]
input_delta = [x - y for x, y in zip(lp["ffn_x"], rp["ffn_x"])]
output_delta = [x - y for x, y in zip(lp["ffn_y"], rp["ffn_y"])]
result = {
    "schema": 1,
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "quantization": "IQ1_M",
    "layer": 2,
    "position": POSITION,
    "token_id": TOKEN_ID,
    "arms": list(ARMS),
    "prompt_sha256": left["request"]["prompt_sha256"],
    "completion_ids_equal": True,
    "topk_ids_equal": lr["ids"] == rr["ids"],
    "topk_ids": lr["ids"],
    "router_weights_bitwise_equal": weights_l == weights_r,
    "router_weight_different_count": sum(x != y for x, y in zip(weights_l, weights_r)),
    "router_weight_max_abs_delta": max(abs(x - y) for x, y in zip(weights_l, weights_r)),
    "device_ffn_x_bitwise_equal": lp["ffn_x"] == rp["ffn_x"],
    "device_ffn_x_different_values": sum(x != y for x, y in zip(lp["ffn_x"], rp["ffn_x"])),
    "device_ffn_x_max_abs_delta": max(map(abs, input_delta)),
    "device_ffn_y_bitwise_equal": lp["ffn_y"] == rp["ffn_y"],
    "device_ffn_y_different_values": sum(x != y for x, y in zip(lp["ffn_y"], rp["ffn_y"])),
    "device_ffn_y_max_abs_delta": max(map(abs, output_delta)),
    "supervision": {name: {"minimum_host_gib": arms[name]["supervisor"]["minimum_available_bytes"] / 2**30,
                           "minimum_admission_gib": arms[name]["supervisor"]["minimum_admission_available_bytes"] / 2**30,
                           "memory_events_max": arms[name]["memory_events"]}
                    for name in ARMS},
    "interpretation": "The layer-2 input is already different, so this pair cannot isolate layer-2 arithmetic. Together with the matched-input layer-1 weighted reconstruction, it locates a downstream activation/router change after the layer-1 output.",
}
if result["device_ffn_x_bitwise_equal"] or result["router_weights_bitwise_equal"] or not result["topk_ids_equal"]:
    raise SystemExit("observed capture does not match the expected layer-2 upstream-change pattern")
out = CAMPAIGN / "analysis-upstream-difference.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
