#!/usr/bin/env python3
"""Compare host route captures with verifier device-side ffn_x/ffn_y rows."""
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/position-keyed-three-arm"
HEADER = struct.Struct('<8sIiiqQQQQQ8i')
ARMS = ("cpu_default", "cpu_mirror", "gpu_layer1")

def delta(a, b):
    diffs = [abs(x - y) for x, y in zip(a, b)]
    return {"exact": a == b, "different_values": sum(x != y for x, y in zip(a, b)),
            "max_abs": max(diffs, default=0.0),
            "relative_l1": math.fsum(diffs) / max(math.fsum(abs(x) for x in a), 1e-30)}

def read_device_rows(path):
    data = path.read_bytes(); offset = 0; rows = {}
    while offset < len(data):
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b'STGDIAG4' or version != 4 or layer != 1 or not 0 < count <= 8:
            raise ValueError(f'{path}: unexpected STGDIAG4 record')
        base = count*n + 2*count*c + 2*count*hv + 2*count*zv
        ffn_x_offset = offset + (base + count*n)*4
        ffn_y_offset = ffn_x_offset + count*n*4
        for i in range(count):
            pos = pos0 + i
            rows[pos] = {
                "token": tokens[i],
                "ffn_x": struct.unpack_from(f'<{n}f', data, ffn_x_offset + i*n*4),
                "ffn_y": struct.unpack_from(f'<{n}f', data, ffn_y_offset + i*n*4),
            }
        offset += count * (4*n + 2*c + 2*hv + 2*zv) * 4
    return rows

routes = {}; device = {}
for arm in ARMS:
    result = CAMPAIGN / arm / "result"
    route_rows = [json.loads(line) for line in (result / "layer1.jsonl").read_text().splitlines()[1:]]
    routes[arm] = {(r["layer"], r["position"], r["token_id"]): r for r in route_rows}
    device[arm] = read_device_rows(result / "combined-moe.bin")

layers = []
for layer in range(48):
    key = (layer, 511, 271)
    d, m, g = (routes[arm][key] for arm in ARMS)
    layers.append({
        "layer": layer,
        "default_mirror_input_equal": d["activation"] == m["activation"],
        "mirror_gpu_input": delta(m["activation"], g["activation"]),
        "gpu_input_equals_previous_gpu_layer_input":
            layer > 0 and g["activation"] == routes["gpu_layer1"][(layer-1,511,271)]["activation"],
        "expert_ids_equal_all_arms": d["ids"] == m["ids"] == g["ids"],
        "owners_equal_default_mirror": d["route_kind"] == m["route_kind"],
    })

stale_capture_positions = []
for pos in sorted(set(device["gpu_layer1"]) & set(device["cpu_mirror"])):
    token = device["gpu_layer1"][pos]["token"]
    l1 = routes["gpu_layer1"].get((1, pos, token))
    l0 = routes["gpu_layer1"].get((0, pos, token))
    if l1 is not None and l0 is not None and all(k >= 0 for k in l1["route_kind"]) and l1["activation"] == l0["activation"]:
        stale_capture_positions.append(pos)

positions = []
for pos in sorted(device["cpu_mirror"]):
    m = device["cpu_mirror"][pos]; g = device["gpu_layer1"][pos]
    entry = {"position": pos, "token_id": m["token"],
             "device_ffn_x_mirror_gpu": delta(m["ffn_x"], g["ffn_x"]),
             "combined_ffn_y_mirror_gpu": delta(m["ffn_y"], g["ffn_y"])}
    for arm in ARMS:
        route = routes[arm].get((1, pos, m["token"]))
        if route is not None:
            entry[f"{arm}_route_input_vs_device_ffn_x"] = delta(m["ffn_x"], route["activation"])
            entry[f"{arm}_cpu_owned_experts"] = [e for e,k in zip(route["ids"],route["route_kind"]) if k < 0]
    positions.append(entry)

out = {
    "source_campaign": str(CAMPAIGN.relative_to(ROOT)),
    "keyed_layer0_to_layer47_example": {"position": 511, "token_id": 271},
    "layer_count": len(layers),
    "layer0_inputs_and_routes_match_all_arms": all(
        routes[a][(0,511,271)]["activation"] == routes[ARMS[0]][(0,511,271)]["activation"] and
        routes[a][(0,511,271)]["ids"] == routes[ARMS[0]][(0,511,271)]["ids"] and
        routes[a][(0,511,271)]["route_kind"] == routes[ARMS[0]][(0,511,271)]["route_kind"] for a in ARMS),
    "gpu_layer1_host_capture_equals_layer0_host_capture":
        routes["gpu_layer1"][(1,511,271)]["activation"] == routes["gpu_layer1"][(0,511,271)]["activation"],
    "gpu_layer1_host_capture_stale_positions": stale_capture_positions,
    "gpu_layer1_device_ffn_x_matches_cpu_mirror_for_all_16_rows": all(
        device["gpu_layer1"][p]["ffn_x"] == device["cpu_mirror"][p]["ffn_x"] for p in device["cpu_mirror"]),
    "layer1_device_rows": positions,
    "first_cpu_mirror_vs_gpu_combined_ffn_y_difference": next(
        (p["position"] for p in positions if not p["combined_ffn_y_mirror_gpu"]["exact"]), None),
    "cpu_mirror_vs_gpu_combined_ffn_y_equal_positions": [p["position"] for p in positions if p["combined_ffn_y_mirror_gpu"]["exact"]],
    "cpu_mirror_vs_gpu_combined_ffn_y_different_positions": [p["position"] for p in positions if not p["combined_ffn_y_mirror_gpu"]["exact"]],
    "layer1_example_ffn_y_mirror_gpu": delta(device["cpu_mirror"][511]["ffn_y"],device["gpu_layer1"][511]["ffn_y"]),
    "layer_details_position_511": layers,
    "interpretation": "The host MoE route capture is stale for all-GPU layer-1 rows at positions 511 and 513: it repeats the same-position layer-0 input. The verifier device-side ffn_x shows the actual GPU-profile MoE input equals the CPU-mirror input bitwise across all 16 decode rows. Combined ffn_y matches at 511 and 513; it first differs at 512, matches again at 513, then differs at 514–526. Per-expert parity shows Q8_1 CPU equals CUDA for all tested experts. At 512, expert 90 remains CPU-default in the GPU-profile arm while the experts moved from CPU mirror to GPU have exact Q8_1/CUDA parity. At 514, experts 30, 159 and 182 remain CPU-owned but use default CPU math in the GPU-profile arm instead of Q8_1. This strongly supports CPU activation-format math as the source of those row-level combined-output differences, without proving a complete weighted-sum decomposition or the later persistent-state divergence cause.",
}
path = HERE / "activation-chain-analysis.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({k:v for k,v in out.items() if k not in ("layer1_device_rows","layer_details_position_511")}, indent=2))
