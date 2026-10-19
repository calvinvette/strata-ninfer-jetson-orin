#!/usr/bin/env python3
"""Join device-side layer-9 verifier rows to host route captures."""
import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/layer9-device-pair"
ARMS = ("cpu_mirror", "gpu_layer1")
HEADER = struct.Struct("<8sIiiqQQQQQ8i")


def device_rows(path):
    data = path.read_bytes()
    offset = 0
    rows = {}
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError(f"{path}: truncated header")
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STGDIAG4" or version != 4 or layer != 9 or not 0 < count <= 8 or n != 2560:
            raise ValueError(f"{path}: invalid layer-9 STGDIAG4 record")
        payload = count * (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        if offset + payload > len(data):
            raise ValueError(f"{path}: truncated record payload")
        x_at = offset + (2 * count * n + 2 * count * c + 2 * count * hv + 2 * count * zv) * 4
        y_at = x_at + count * n * 4
        for i in range(count):
            position = pos0 + i
            if position in rows:
                raise ValueError(f"{path}: duplicate position {position}")
            rows[position] = {
                "token_id": tokens[i],
                "ffn_x": struct.unpack_from(f"<{n}f", data, x_at + i * n * 4),
                "ffn_y": struct.unpack_from(f"<{n}f", data, y_at + i * n * 4),
            }
        offset += payload
    if sorted(rows) != list(range(511, 527)):
        raise ValueError(f"{path}: expected positions 511–526, found {sorted(rows)}")
    return rows


def max_delta(a, b):
    return max((abs(x - y) for x, y in zip(a, b)), default=0.0)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN,
                    help="campaign directory containing the two arm subdirectories")
CAMPAIGN = parser.parse_args().campaign.resolve()

arms = {}
for arm in ARMS:
    folder = CAMPAIGN / arm
    result = folder / "result"
    request = json.loads((result / "requests.json").read_text())
    routes_lines = (result / "routes-all-layers.jsonl").read_text().splitlines()
    if json.loads(routes_lines[0]).get("format") != "strata-moe-dispatch-v3":
        raise ValueError(f"{arm}: unexpected route format")
    route = {(x["layer"], x["position"]): x for x in map(json.loads, routes_lines[1:])}
    if len(routes_lines) != 769 or len([k for k in route if k[0] == 9]) != 16:
        raise ValueError(f"{arm}: incomplete route trace")
    device = device_rows(result / "combined-moe.bin")
    supervisor = json.loads((folder / "supervisor/result.json").read_text())
    samples = [json.loads(x) for x in (folder / "supervisor/memory.jsonl").read_text().splitlines()]
    scoped = [cg for sample in samples for cg in sample.get("cgroups", []) if cg.get("max_bytes") == 28 * 1024**3]
    events = {k: max((cg.get("memory_events", {}).get(k, 0) for cg in scoped), default=0)
              for k in ("high", "max", "oom", "oom_kill")}
    if supervisor["status"] != "pass" or any(events.values()):
        raise ValueError(f"{arm}: failed supervision or nonzero cgroup events")
    arms[arm] = {"request": request, "routes": route, "device": device,
                 "supervisor": supervisor, "samples": len(samples), "memory_events": events}

if len({arms[a]["request"]["prompt_sha256"] for a in ARMS}) != 1:
    raise ValueError("prompt hashes differ")
if arms[ARMS[0]]["request"]["completion_ids"] != arms[ARMS[1]]["request"]["completion_ids"]:
    raise ValueError("completion IDs differ")

rows = []
for position in range(511, 527):
    left, right = (arms[a]["device"][position] for a in ARMS)
    route_rows = [arms[a]["routes"][(9, position)] for a in ARMS]
    for arm, d, r in zip(ARMS, (left, right), route_rows):
        host_as_f32 = tuple(struct.unpack("<f", struct.pack("<f", float(v)))[0] for v in r["activation"])
        if r["token_id"] != d["token_id"]:
            raise ValueError(f"{arm}: device/route token mismatch at {position}")
        if len(host_as_f32) != len(d["ffn_x"]):
            raise ValueError(f"{arm}: route/device activation width mismatch")
    rows.append({
        "position": position,
        "token_id": left["token_id"],
        "host_route_ids_equal": route_rows[0]["ids"] == route_rows[1]["ids"],
        "host_route_owners_equal": route_rows[0]["route_kind"] == route_rows[1]["route_kind"],
        "device_ffn_x_equal": left["ffn_x"] == right["ffn_x"],
        "device_ffn_x_max_abs_delta": max_delta(left["ffn_x"], right["ffn_x"]),
        "device_ffn_y_equal": left["ffn_y"] == right["ffn_y"],
        "device_ffn_y_max_abs_delta": max_delta(left["ffn_y"], right["ffn_y"]),
        "route_capture_matches_device_ffn_x": [
            tuple(struct.unpack("<f", struct.pack("<f", float(v)))[0] for v in route_rows[i]["activation"])
            == arms[arm]["device"][position]["ffn_x"]
            for i, arm in enumerate(ARMS)],
    })

out = {
    "schema": 1,
    "campaign": str(CAMPAIGN.relative_to(ROOT)),
    "device_capture_layer": 9,
    "prompt_sha256": arms[ARMS[0]]["request"]["prompt_sha256"],
    "completion_ids_equal": True,
    "arm_order": (CAMPAIGN / "order.txt").read_text().strip(),
    "arms": {a: {"minimum_host_gib": arms[a]["supervisor"]["minimum_available_bytes"] / 2**30,
                 "minimum_admission_gib": arms[a]["supervisor"]["minimum_admission_available_bytes"] / 2**30,
                 "samples": arms[a]["samples"], "memory_events_max": arms[a]["memory_events"]}
             for a in ARMS},
    "rows": rows,
    "first_device_ffn_x_difference_position": next((r["position"] for r in rows if not r["device_ffn_x_equal"]), None),
    "first_device_ffn_y_difference_position": next((r["position"] for r in rows if not r["device_ffn_y_equal"]), None),
    "device_ffn_x_matches_host_route_all_rows": all(all(r["route_capture_matches_device_ffn_x"]) for r in rows),
}
path = CAMPAIGN / "analysis-layer9.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"output": str(path),
                  "first_device_ffn_x_difference_position": out["first_device_ffn_x_difference_position"],
                  "first_device_ffn_y_difference_position": out["first_device_ffn_y_difference_position"],
                  "device_ffn_x_matches_host_route_all_rows": out["device_ffn_x_matches_host_route_all_rows"]}, indent=2))
