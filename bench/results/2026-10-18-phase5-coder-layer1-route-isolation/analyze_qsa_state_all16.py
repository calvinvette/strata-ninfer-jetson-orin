#!/usr/bin/env python3
"""Align per-QSA accepted-prefix state fingerprints with the all-layer route trace."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/qsa-state-three-arm"
ARMS = ("cpu_default", "cpu_mirror", "gpu_layer1")
PAIRS = (("cpu_default", "cpu_mirror"), ("cpu_mirror", "gpu_layer1"))

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN,
                    help="campaign directory containing the three arm subdirectories")
CAMPAIGN = parser.parse_args().campaign.resolve()


def load_arm(arm):
    folder = CAMPAIGN / arm
    result = folder / "result"
    requests = json.loads((result / "requests.json").read_text())
    lines = (result / "service.log").read_text(errors="replace").splitlines()
    qsa_by_length = {}
    pattern = re.compile(r"STATE_HASH_QSA_LAYERS L=(\d+)\s+(.*)")
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        length = int(match.group(1))
        records = [(int(q), int(layer), digest) for q, layer, digest in
                   re.findall(r"qsa=(\d+) layer=(\d+) hash=([0-9a-f]{16})", match.group(2))]
        if len(records) != 12 or [x[0] for x in records] != list(range(12)):
            raise ValueError(f"{arm}: expected 12 ordered QSA layer hashes at L={length}")
        if [x[1] for x in records] != list(range(3, 48, 4)):
            raise ValueError(f"{arm}: unexpected QSA ordinal-to-layer map at L={length}")
        if length in qsa_by_length:
            raise ValueError(f"{arm}: duplicate QSA fingerprint at L={length}")
        qsa_by_length[length] = {layer: digest for _, layer, digest in records}
    if sorted(qsa_by_length) != list(range(512, 528)):
        raise ValueError(f"{arm}: expected accepted-prefix QSA hashes for L=512..527")

    route_lines = (result / "routes-all-layers.jsonl").read_text().splitlines()
    if json.loads(route_lines[0]).get("format") != "strata-moe-dispatch-v3":
        raise ValueError(f"{arm}: unexpected route capture format")
    route_rows = [json.loads(line) for line in route_lines[1:]]
    routes = {(x["layer"], x["position"]): x for x in route_rows}
    if len(route_rows) != 768 or len(routes) != 768:
        raise ValueError(f"{arm}: incomplete all-layer route capture")
    supervisor = json.loads((folder / "supervisor/result.json").read_text())
    samples = [json.loads(x) for x in (folder / "supervisor/memory.jsonl").read_text().splitlines()]
    scope = [cg for sample in samples for cg in sample.get("cgroups", [])
             if cg.get("max_bytes") == 28 * 1024**3]
    events = {k: max((cg.get("memory_events", {}).get(k, 0) for cg in scope), default=0)
              for k in ("high", "max", "oom", "oom_kill")}
    if supervisor["status"] != "pass" or any(events.values()):
        raise ValueError(f"{arm}: supervision failed or cgroup events were nonzero")
    return {"requests": requests, "qsa": qsa_by_length, "routes": routes,
            "supervisor": supervisor, "samples": len(samples), "memory_events": events}


arms = {arm: load_arm(arm) for arm in ARMS}
if len({a["requests"]["prompt_sha256"] for a in arms.values()}) != 1:
    raise ValueError("prompt hashes differ")
token_ids = [a["requests"]["completion_ids"] for a in arms.values()]
if any(ids != token_ids[0] for ids in token_ids[1:]):
    raise ValueError("completion token IDs differ")

pairs = {}
for left, right in PAIRS:
    rows = []
    for position in range(511, 527):
        length = position + 1
        qsa_diffs = [layer for layer in range(3, 48, 4)
                     if arms[left]["qsa"][length][layer] != arms[right]["qsa"][length][layer]]
        route_first = None
        for layer in range(48):
            a = arms[left]["routes"][(layer, position)]
            b = arms[right]["routes"][(layer, position)]
            if a["token_id"] != b["token_id"]:
                raise ValueError(f"{left}/{right}: input token mismatch at layer={layer}, position={position}")
            if left == "cpu_mirror" and right == "gpu_layer1" and layer == 1 and position in (511, 513):
                continue  # independently established stale host callback rows on the all-GPU route
            if max(abs(float(x) - float(y)) for x, y in zip(a["activation"], b["activation"])) > 1e-7:
                route_first = layer
                break
        rows.append({
            "position": position,
            "first_differing_qsa_model_layer": qsa_diffs[0] if qsa_diffs else None,
            "different_qsa_model_layers": qsa_diffs,
            "first_differing_host_route_activation_layer": route_first,
            "qsa_and_route_first_layers_equal": bool(qsa_diffs) and qsa_diffs[0] == route_first,
        })
    pairs[f"{left}_vs_{right}"] = rows

out = {
    "schema": 1,
    "campaign": str(CAMPAIGN.relative_to(ROOT)),
    "qsa_state_fingerprint": "FNV-1a 64-bit over idx_tail, idx_dead, idx_pooled including spare row, and the used K/V cells for that QSA state",
    "hash_limit": "Hashes localize state differences; equal 64-bit hashes do not prove byte identity.",
    "qsa_ordinal_to_model_layer": list(range(3, 48, 4)),
    "prompt_sha256": arms[ARMS[0]]["requests"]["prompt_sha256"],
    "completion_ids_equal": True,
    "arm_order": (CAMPAIGN / "order.txt").read_text().strip(),
    "arms": {arm: {"samples": arms[arm]["samples"],
                   "minimum_host_gib": arms[arm]["supervisor"]["minimum_available_bytes"] / 2**30,
                   "minimum_admission_gib": arms[arm]["supervisor"]["minimum_admission_available_bytes"] / 2**30,
                   "memory_events_max": arms[arm]["memory_events"]} for arm in ARMS},
    "pairs": pairs,
}
output = CAMPAIGN / "analysis-qsa-state.json"
output.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"output": str(output), "pair_first_differing_qsa_layers": {
    pair: [row["first_differing_qsa_model_layer"] for row in rows]
    for pair, rows in pairs.items()}, "qsa_and_route_first_layers_equal": {
    pair: sum(row["qsa_and_route_first_layers_equal"] for row in rows)
    for pair, rows in pairs.items()}}, indent=2))
