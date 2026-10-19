#!/usr/bin/env python3
"""Compare matched layer-8 route inputs, CPU expert rows, and device combine outputs."""
import argparse
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/layer8-output-pair"
ARMS = ("cpu_mirror", "gpu_layer1")
HEADER = struct.Struct("<8sIiiqQQQQQ8i")


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
            raise ValueError(f"{path}: truncated diagnostic payload")
        x_at = offset + (2 * count * n + 2 * count * c + 2 * count * hv + 2 * count * zv) * 4
        y_at = x_at + count * n * 4
        for i in range(count):
            position = pos0 + i
            if position in rows:
                raise ValueError(f"{path}: duplicate device row {position}")
            rows[position] = {
                "token_id": tokens[i],
                "ffn_x": struct.unpack_from(f"<{n}f", data, x_at + i * n * 4),
                "ffn_y": struct.unpack_from(f"<{n}f", data, y_at + i * n * 4),
            }
        offset += payload
    if sorted(rows) != list(range(511, 527)):
        raise ValueError(f"{path}: expected positions 511–526")
    return rows


def delta(a, b):
    diffs = [abs(x - y) for x, y in zip(a, b)]
    return {"exact": list(a) == list(b), "different_values": sum(x != y for x, y in zip(a, b)),
            "max_abs": max(diffs, default=0.0),
            "relative_l1": math.fsum(diffs) / max(math.fsum(abs(x) for x in a), 1e-30)}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
CAMPAIGN = parser.parse_args().campaign.resolve()
arms = {}
for arm in ARMS:
    folder = CAMPAIGN / arm
    result = folder / "result"
    request = json.loads((result / "requests.json").read_text())
    route_lines = (result / "routes-all-layers.jsonl").read_text().splitlines()
    if json.loads(route_lines[0]).get("format") != "strata-moe-dispatch-v3":
        raise ValueError(f"{arm}: unexpected route schema")
    all_routes = [json.loads(line) for line in route_lines[1:]]
    routes = {(r["layer"], r["position"]): r for r in all_routes}
    if len(all_routes) != 768 or len(routes) != 768:
        raise ValueError(f"{arm}: incomplete route trace")
    output_lines = (result / "cpu-outputs-layer8.jsonl").read_text().splitlines()
    if json.loads(output_lines[0]).get("format") != "strata-moe-cpu-output-v2":
        raise ValueError(f"{arm}: unexpected CPU output schema")
    outputs = {}
    for line in output_lines[1:]:
        row = json.loads(line)
        if row["layer"] != 8:
            raise ValueError(f"{arm}: non-layer-8 CPU output row")
        key = (row["position"], row["token_id"], row["expert"])
        if key in outputs:
            raise ValueError(f"{arm}: duplicate CPU output row {key}")
        route = routes.get((8, row["position"]))
        if route is None or route["token_id"] != row["token_id"] or row["expert"] not in route["ids"]:
            raise ValueError(f"{arm}: CPU output does not match a layer-8 route {key}")
        slot = route["ids"].index(row["expert"])
        if route["route_kind"][slot] >= 0 or route["dispatch"] != row["dispatch"]:
            raise ValueError(f"{arm}: CPU output is not its matching CPU-owned route {key}")
        outputs[key] = row["output"]
    device = read_device(result / "combined-moe.bin")
    supervisor = json.loads((folder / "supervisor/result.json").read_text())
    samples = [json.loads(x) for x in (folder / "supervisor/memory.jsonl").read_text().splitlines()]
    scoped = [cg for s in samples for cg in s.get("cgroups", []) if cg.get("max_bytes") == 28 * 1024**3]
    events = {k: max((cg.get("memory_events", {}).get(k, 0) for cg in scoped), default=0)
              for k in ("high", "max", "oom", "oom_kill")}
    if supervisor["status"] != "pass" or any(events.values()):
        raise ValueError(f"{arm}: failed supervision or nonzero cgroup events")
    arms[arm] = {"request": request, "routes": routes, "outputs": outputs, "device": device,
                 "supervisor": supervisor, "samples": len(samples), "memory_events": events}

if arms[ARMS[0]]["request"]["prompt_sha256"] != arms[ARMS[1]]["request"]["prompt_sha256"]:
    raise ValueError("prompt hashes differ")
if arms[ARMS[0]]["request"]["completion_ids"] != arms[ARMS[1]]["request"]["completion_ids"]:
    raise ValueError("completion IDs differ")

rows = []
for position in range(511, 527):
    left, right = (arms[a]["device"][position] for a in ARMS)
    lr, rr = (arms[a]["routes"][(8, position)] for a in ARMS)
    lx = tuple(struct.unpack("<f", struct.pack("<f", float(v)))[0] for v in lr["activation"])
    rx = tuple(struct.unpack("<f", struct.pack("<f", float(v)))[0] for v in rr["activation"])
    if left["token_id"] != lr["token_id"] or right["token_id"] != rr["token_id"]:
        raise ValueError(f"device/route token mismatch at {position}")
    if left["ffn_x"] != lx or right["ffn_x"] != rx:
        raise ValueError(f"host route capture does not match device ffn_x at {position}")
    keys = sorted(set(arms[ARMS[0]]["outputs"]) & set(arms[ARMS[1]]["outputs"]))
    keys = [k for k in keys if k[0] == position]
    expert_deltas = []
    for key in keys:
        diff = delta(arms[ARMS[0]]["outputs"][key], arms[ARMS[1]]["outputs"][key])
        expert_deltas.append({"expert": key[2], **diff})
    rows.append({
        "position": position,
        "token_id": left["token_id"],
        "route_activation_exact": lx == rx,
        "route_ids_equal": lr["ids"] == rr["ids"],
        "route_owners_equal": lr["route_kind"] == rr["route_kind"],
        "cpu_owned_experts_mirror": [e for e, owner in zip(lr["ids"], lr["route_kind"]) if owner < 0],
        "cpu_owned_experts_gpu_profile": [e for e, owner in zip(rr["ids"], rr["route_kind"]) if owner < 0],
        "common_cpu_output_rows": len(keys),
        "cpu_expert_output_deltas": expert_deltas,
        "device_ffn_x_delta": delta(left["ffn_x"], right["ffn_x"]),
        "device_ffn_y_delta": delta(left["ffn_y"], right["ffn_y"]),
    })

out = {
    "schema": 1,
    "campaign": str(CAMPAIGN.relative_to(ROOT)),
    "device_layer": 8,
    "cpu_output_layer": 8,
    "prompt_sha256": arms[ARMS[0]]["request"]["prompt_sha256"],
    "completion_ids_equal": True,
    "arm_order": (CAMPAIGN / "order.txt").read_text().strip(),
    "arms": {a: {"samples": arms[a]["samples"],
                 "minimum_host_gib": arms[a]["supervisor"]["minimum_available_bytes"] / 2**30,
                 "minimum_admission_gib": arms[a]["supervisor"]["minimum_admission_available_bytes"] / 2**30,
                 "memory_events_max": arms[a]["memory_events"]} for a in ARMS},
    "rows": rows,
}
output = CAMPAIGN / "analysis-layer8.json"
output.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({
    "output": str(output),
    "position_511": rows[0],
    "first_device_ffn_y_difference_position": next((r["position"] for r in rows if not r["device_ffn_y_delta"]["exact"]), None),
}, indent=2))
