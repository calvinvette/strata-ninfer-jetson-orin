#!/usr/bin/env python3
"""Reconstruct the layer-2 combined delta from captured per-expert verifier rows."""
import json
import math
import argparse
import gzip
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/service-parts-confirm3/owner-confirm3-retry1/block-20261021"
ARMS = ("cpu_mirror", "gpu_layer2")
POSITION = 511
TOKEN_ID = 271
PARTS_HEADER = struct.Struct("<8sIIIIQq8i")
GDN_HEADER = struct.Struct("<8sIiiqQQQQQ8i")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN,
                    help="directory containing cpu_mirror/ and gpu_layer2/ result/supervisor folders")
parser.add_argument("--output", type=Path, help="write reviewed JSON here (default: analysis-service-parts.json in campaign parent)")
args = parser.parse_args()
CAMPAIGN = args.campaign.resolve()


def read_parts(path):
    raw = read_bytes(path)
    off = 0
    rows = {}
    while off < len(raw):
        if off + PARTS_HEADER.size > len(raw):
            raise ValueError(f"{path}: truncated parts header")
        magic, version, layer, count, k, n, pos0, *tokens = PARTS_HEADER.unpack_from(raw, off)
        off += PARTS_HEADER.size
        if magic != b"STMPART1" or version != 1 or layer != 2 or not 0 < count <= 8 or k != 10 or n != 2560:
            raise ValueError(f"{path}: invalid STMPART1 record")
        size = count * k * n * 4
        if off + size > len(raw):
            raise ValueError(f"{path}: truncated parts payload")
        values = struct.unpack_from(f"<{count*k*n}f", raw, off)
        for row in range(count):
            pos = pos0 + row
            if pos in rows:
                raise ValueError(f"{path}: duplicate position {pos}")
            start = row * k * n
            rows[pos] = {"token_id": tokens[row],
                         "experts": [values[start + j*n:start + (j+1)*n] for j in range(k)]}
        off += size
    return rows


def read_gdn(path):
    raw = read_bytes(path)
    off = 0
    rows = {}
    while off < len(raw):
        if off + GDN_HEADER.size > len(raw):
            raise ValueError(f"{path}: truncated STGDIAG4 header")
        h = GDN_HEADER.unpack_from(raw, off)
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = h
        if magic != b"STGDIAG4" or version != 4 or layer != 2 or not 0 < count <= 8 or n != 2560:
            raise ValueError(f"{path}: invalid layer-2 STGDIAG4 record")
        off += GDN_HEADER.size
        payload = count * (4*n + 2*c + 2*hv + 2*zv) * 4
        x_at = off + (2*count*n + 2*count*c + 2*count*hv + 2*count*zv) * 4
        y_at = x_at + count*n*4
        if off + payload > len(raw):
            raise ValueError(f"{path}: truncated GDN payload")
        for i in range(count):
            rows[pos0 + i] = {"token_id": tokens[i],
                              "ffn_y": struct.unpack_from(f"<{n}f", raw, y_at + i*n*4)}
        off += payload
    return rows


def read_bytes(path):
    return gzip.open(path, "rb").read() if path.suffix == ".gz" else path.read_bytes()


def artifact_path(path):
    return path if path.exists() else path.with_name(path.name + ".gz")


def read_states(path):
    states = []
    for line in path.read_text(errors="replace").splitlines():
        marker = " state={STATE_HASH "
        if "ACCEPTED_PREFIX " not in line or marker not in line:
            continue
        body = line.split(marker, 1)[1].split("}", 1)[0]
        states.append(dict(re.findall(r"(\w+)=([0-9a-f,-]+)", body)))
    return states


arms = {}
for arm in ARMS:
    result_dir = CAMPAIGN / arm / "run"
    route_path = artifact_path(result_dir / "device-moe-routes.jsonl")
    with (gzip.open(route_path, "rt") if route_path.suffix == ".gz" else open(route_path, "rt")) as stream:
        route_lines = stream.read().splitlines()
    route_head = json.loads(route_lines[0])
    if route_head != {"format": "strata-verify-moe-route-v1", "k": 10}:
        raise ValueError(f"{arm}: unexpected route schema")
    routes = {r["position"]: r for r in map(json.loads, route_lines[1:])}
    parts = read_parts(artifact_path(result_dir / "device-moe-parts.bin"))
    gdn = read_gdn(artifact_path(result_dir / "combined-moe.bin"))
    request = json.loads((result_dir / "requests.json").read_text())
    supervisor_path = CAMPAIGN / arm / "supervisor" / "result.json"
    supervisor = json.loads(supervisor_path.read_text())
    memory_path = CAMPAIGN / arm / "supervisor" / "memory.jsonl"
    if not memory_path.exists():
        memory_path = memory_path.with_suffix(".jsonl.gz")
        opener = gzip.open
    else:
        opener = open
    with opener(memory_path, "rt") as stream:
        memory_samples = [json.loads(line) for line in stream if line.strip()]
    scoped_cgroups = [cg for sample in memory_samples for cg in sample.get("cgroups", [])
                      if cg.get("max_bytes") == 28 * 2**30]
    event_names = ("high", "max", "oom", "oom_kill")
    event_max = {key: max((cg.get("memory_events", {}).get(key, 0) for cg in scoped_cgroups), default=0)
                 for key in event_names}
    states = read_states(result_dir / "service.log")
    if set(routes) != set(parts) or set(parts) != set(gdn):
        raise ValueError(f"{arm}: route/parts/GDN positions differ")
    for pos, row in parts.items():
        if routes[pos]["layer"] != 2 or routes[pos]["token_id"] != row["token_id"] or gdn[pos]["token_id"] != row["token_id"]:
            raise ValueError(f"{arm}: row identity mismatch at position {pos}")
        if len(routes[pos]["ids"]) != 10 or len(routes[pos]["weights"]) != 10:
            raise ValueError(f"{arm}: invalid route width at position {pos}")
    if (supervisor.get("status") != "pass" or supervisor.get("minimum_available_bytes", 0) < 6 * 2**30 or
            supervisor.get("minimum_admission_available_bytes", 0) < 6 * 2**30 or any(event_max.values()) or
            not memory_samples):
        raise ValueError(f"{arm}: supervised run failed or breached six-GiB physical headroom")
    if len(states) != request.get("accepted_prefix_records"):
        raise ValueError(f"{arm}: accepted-prefix state log count differs from request summary")
    if len(states) < 16:
        raise ValueError(f"{arm}: too few accepted-prefix state records")
    arms[arm] = {"routes": routes, "parts": parts, "gdn": gdn, "request": request,
                 "states": states, "supervisor": supervisor, "memory_samples": len(memory_samples),
                 "memory_events_max": event_max}

a, b = (arms[name] for name in ARMS)
if a["request"]["prompt_sha256"] != b["request"]["prompt_sha256"]:
    raise ValueError("prompt hashes differ")
if a["parts"][POSITION]["token_id"] != TOKEN_ID or b["parts"][POSITION]["token_id"] != TOKEN_ID:
    raise ValueError("position-511 token differs from expected input")
la, lb = a["routes"][POSITION], b["routes"][POSITION]
if a["request"]["completion_ids"] != b["request"]["completion_ids"]:
    raise ValueError("completion IDs differ across owner arms")
if a["states"] != b["states"]:
    mismatch = next((i for i, (x, y) in enumerate(zip(a["states"], b["states"])) if x != y), None)
    raise ValueError(f"accepted-prefix state fingerprints differ at row {mismatch}")
per_position = []
for pos in sorted(a["parts"]):
    ra, rb = a["routes"][pos], b["routes"][pos]
    if ra["ids"] != rb["ids"] or ra["weights"] != rb["weights"]:
        raise ValueError(f"device route differs at position {pos}")
    part_diffs = sum(x != y for ex, ey in zip(a["parts"][pos]["experts"], b["parts"][pos]["experts"])
                     for x, y in zip(ex, ey))
    ffn_diffs = sum(x != y for x, y in zip(a["gdn"][pos]["ffn_y"], b["gdn"][pos]["ffn_y"]))
    weighted_delta = [0.0] * 2560
    for j, weight in enumerate(ra["weights"]):
        for i, (x, y) in enumerate(zip(a["parts"][pos]["experts"][j], b["parts"][pos]["experts"][j])):
            weighted_delta[i] += float(weight) * (x-y)
    actual = [x-y for x, y in zip(a["gdn"][pos]["ffn_y"], b["gdn"][pos]["ffn_y"])]
    residual = [x-y for x, y in zip(actual, weighted_delta)]
    actual_l1 = math.fsum(abs(x) for x in actual)
    residual_l1 = math.fsum(abs(x) for x in residual)
    per_position.append({"position": pos, "token_id": ra["token_id"], "part_value_differences": part_diffs,
                         "combined_ffn_y_value_differences": ffn_diffs,
                         "combined_delta_l1": actual_l1, "weighted_parts_residual_relative_l1":
                         residual_l1 / max(actual_l1, 1e-30)})
result = {
    "schema": 2, "campaign": str(CAMPAIGN), "position": POSITION, "token_id": TOKEN_ID,
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e", "quantization": "IQ1_M",
    "route_ids_and_weights_equal_all_positions": True,
    "completion_ids_equal": True, "accepted_prefix_state_equal": True,
    "accepted_prefix_records": len(a["states"]),
    "minimum_host_gib_by_arm": {arm: arms[arm]["supervisor"]["minimum_available_bytes"] / 2**30 for arm in ARMS},
    "minimum_admission_gib_by_arm": {arm: arms[arm]["supervisor"].get("minimum_admission_available_bytes", 0) / 2**30 for arm in ARMS},
    "memory_sample_count_by_arm": {arm: arms[arm]["memory_samples"] for arm in ARMS},
    "memory_events_max_by_arm": {arm: arms[arm]["memory_events_max"] for arm in ARMS},
    "per_position": per_position,
    "scope": "same-source matched-capacity fixed-residency owner pair; all captured device routes, per-expert rows, combined ffn_y and accepted-prefix state records"
}
out = args.output.resolve() if args.output else CAMPAIGN.parent / "analysis-service-parts.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
