#!/usr/bin/env python3
"""Verify route/CPU/combined row keys and summarize the current-source triplet."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "position-keyed-three-arm"
sys.path.insert(0, str(ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace"))
from analyze_combined_moe import read_combined, read_jsonl  # noqa: E402


def summary_delta(x, y):
    diffs = [abs(a - b) for a, b in zip(x, y)]
    return {
        "exact": all(a == b for a, b in zip(x, y)),
        "different_values": sum(a != b for a, b in zip(x, y)),
        "elements": len(x),
        "max_abs": max(diffs, default=0.0),
        "relative_l1": math.fsum(diffs) / max(math.fsum(abs(a) for a in x), 1e-30),
    }


campaign = json.loads((CAMPAIGN / "campaign.json").read_text())
if campaign.get("status") != "complete" or any(r.get("status") != "pass" for r in campaign["runs"]):
    raise RuntimeError("the current-source three-arm campaign is not complete")
arms = {}
for record in campaign["runs"]:
    arm = record["arm"]
    result = CAMPAIGN / arm / "result"
    route_lines = (result / "layer1.jsonl").read_text().splitlines()
    if json.loads(route_lines[0]).get("format") != "strata-moe-dispatch-v3":
        raise RuntimeError(f"{arm} does not have position-keyed route records")
    route = [json.loads(line) for line in route_lines[1:]]
    target = next(r for r in route if r["dispatch"] == 1 and r["layer"] == 1 and r["row"] == 0)
    layer, combined = read_combined(result / "combined-moe.bin")
    if layer != 1:
        raise RuntimeError(f"{arm} combined capture is not layer 1")
    matches = [r for r in combined if r["position"] == target["position"] and r["token"] == target["token_id"]]
    if len(matches) != 1:
        raise RuntimeError(f"{arm} route row matched {len(matches)} combined rows")
    outputs_path = result / "cpu-outputs.jsonl"
    cpu_outputs = read_jsonl(outputs_path) if outputs_path.exists() else []
    target_cpu = [r for r in cpu_outputs if r["dispatch"] == 1 and r["layer"] == 1]
    expected_cpu = {(i, target["ids"][i]) for i, owner in enumerate(target["route_kind"]) if owner < 0}
    if {(r["row"], r["expert"]) for r in target_cpu} != expected_cpu:
        raise RuntimeError(f"{arm} CPU output rows do not match route ownership")
    if any((r["position"], r["token_id"]) != (target["position"], target["token_id"]) for r in target_cpu):
        raise RuntimeError(f"{arm} CPU output rows do not share the route key")
    request = json.loads((result / "requests.json").read_text())
    arms[arm] = {"route": target, "combined": combined, "combined_row": matches[0],
                 "cpu_outputs": target_cpu, "request": request,
                 "minimum_host_available_bytes": record["minimum_host_available_bytes"],
                 "minimum_admission_available_bytes": record["minimum_admission_available_bytes"]}

ref = arms["cpu_default"]
if len({x["request"]["prompt_sha256"] for x in arms.values()}) != 1:
    raise RuntimeError("prompt hashes differ")
if len({tuple(x["request"]["completion_ids"]) for x in arms.values()}) != 1:
    raise RuntimeError("completion token IDs differ")
if len({tuple(x["route"]["ids"]) for x in arms.values()}) != 1:
    raise RuntimeError("routed expert IDs differ")
keys = {(r["position"], r["token_id"]) for r in (x["route"] for x in arms.values())}
if len(keys) != 1:
    raise RuntimeError("route absolute token keys differ")

out = {
    "scope": "randomized three-arm current-source correctness/diagnostic run; one 512-token prompt and 16 output tokens",
    "campaign_order": campaign["order"],
    "binary_sha256": campaign["binary_sha256"],
    "same_prompt_hash": True,
    "same_completion_ids": True,
    "completion_tokens": len(ref["request"]["completion_ids"]),
    "route_to_combined_key": {"position": ref["route"]["position"], "token_id": ref["route"]["token_id"],
                               "matches_per_arm": 1},
    "per_arm": {},
    "joined_row_ffn_y": {},
    "cpu_expert_output_default_vs_mirror": {},
    "pairwise_combined_ffn_y": {},
    "route_input_activation_matches_default": {},
    "persistent_state_matches_default": {},
    "causal_isolation_proven": False,
    "causal_limit": "A shared absolute row key proves alignment, but if changing profile membership changes the activation supplied to the routed layer, this intervention still does not isolate execution-owner arithmetic.",
}
for name, x in arms.items():
    out["per_arm"][name] = {
        "route_owners": x["route"]["route_kind"],
        "cpu_output_rows": len(x["cpu_outputs"]),
        "cpu_output_rows_match_owners_and_key": True,
        "minimum_host_available_gib": x["minimum_host_available_bytes"] / 2**30,
        "minimum_admission_available_gib": x["minimum_admission_available_bytes"] / 2**30,
    }
    out["route_input_activation_matches_default"][name] = x["route"]["activation"] == ref["route"]["activation"]
    out["persistent_state_matches_default"][name] = x["request"]["state"] == ref["request"]["state"]

for left, right in (("cpu_default", "cpu_mirror"), ("cpu_default", "gpu_layer1"), ("cpu_mirror", "gpu_layer1")):
    out["joined_row_ffn_y"][f"{left}_vs_{right}"] = summary_delta(
        arms[left]["combined_row"]["ffn_y"], arms[right]["combined_row"]["ffn_y"])
    a, b = arms[left]["combined"], arms[right]["combined"]
    ka = [(r["position"], r["token"]) for r in a]
    kb = [(r["position"], r["token"]) for r in b]
    if ka != kb:
        raise RuntimeError(f"combined capture keys differ: {left} vs {right}")
    flat_a = [v for row in a for v in row["ffn_y"]]
    flat_b = [v for row in b for v in row["ffn_y"]]
    out["pairwise_combined_ffn_y"][f"{left}_vs_{right}"] = summary_delta(flat_a, flat_b)

cpu_a = {row["row"]: row for row in arms["cpu_default"]["cpu_outputs"]}
cpu_b = {row["row"]: row for row in arms["cpu_mirror"]["cpu_outputs"]}
if cpu_a.keys() != cpu_b.keys():
    raise RuntimeError("CPU default/mirror captured different expert output rows")
for row in sorted(cpu_a):
    a, b = cpu_a[row], cpu_b[row]
    if (a["expert"], a["position"], a["token_id"]) != (b["expert"], b["position"], b["token_id"]):
        raise RuntimeError("CPU output row identity differs")
    out["cpu_expert_output_default_vs_mirror"][str(a["expert"])] = summary_delta(a["output"], b["output"])

out_path = CAMPAIGN / "analysis.json"
out_path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
