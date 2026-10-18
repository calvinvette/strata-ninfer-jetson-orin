#!/usr/bin/env python3
"""Summarize first-row Coder route isolation captures without causal overclaim."""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace"))
from analyze_combined_moe import read_combined, read_jsonl  # noqa: E402

RUNS = {
    "cpu_default": HERE / "retry-start0/cpu_default/result",
    "cpu_mirror": HERE / "retry-start0/cpu_mirror/result",
    "gpu_layer1": HERE / "retry-profile-fixed/gpu_layer1/result",
}


def delta(a, b):
    flat_a = [v for row in a for v in row]
    flat_b = [v for row in b for v in row]
    if len(flat_a) != len(flat_b):
        raise ValueError("tensor lengths differ")
    diffs = [abs(x - y) for x, y in zip(flat_a, flat_b)]
    return {
        "exact": all(x == y for x, y in zip(flat_a, flat_b)),
        "different_values": sum(x != y for x, y in zip(flat_a, flat_b)),
        "elements": len(flat_a),
        "max_abs": max(diffs, default=0.0),
        "relative_l1": math.fsum(diffs) / max(math.fsum(abs(x) for x in flat_a), 1e-30),
    }


loaded = {}
for arm, path in RUNS.items():
    route = read_jsonl(path / "layer1.jsonl")
    layer1_row = next(r for r in route if r["layer"] == 1 and r["dispatch"] == 1)
    layer0_row = next(r for r in route if r["layer"] == 0 and r["dispatch"] == 0)
    layer, combined = read_combined(path / "combined-moe.bin")
    request = json.loads((path / "requests.json").read_text())
    if layer != 1 or len(combined) != 16:
        raise ValueError(f"unexpected combined capture in {arm}")
    loaded[arm] = (route, layer0_row, layer1_row, combined, request)

base = loaded["cpu_default"]
summary = {
    "scope": "three-arm, one 512-token prompt, one 16-token completion; correctness and diagnostic capture only",
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "quantization": "IQ1_M",
    "binary_sha256": (HERE / "binary-sha256.txt").read_text().split()[0],
    "profile_sha256": json.loads((HERE / "profile-design.json").read_text())["output_sha256"],
    "same_prompt_hash": len({x[4]["prompt_sha256"] for x in loaded.values()}) == 1,
    "same_completion_token_ids": len({tuple(x[4]["completion_ids"]) for x in loaded.values()}) == 1,
    "completion_tokens": len(base[4]["completion_ids"]),
    "route_observation": {
        "dispatch": 1,
        "layer": 1,
        "row": 0,
        "n_tok": 1,
        "expert_ids": base[2]["ids"],
        "cpu_default_and_mirror_owners": base[2]["route_kind"],
        "gpu_profile_owners": loaded["gpu_layer1"][2]["route_kind"],
        "cpu_owned_target_pairs": [[1, base[2]["ids"][i]] for i, owner in enumerate(base[2]["route_kind"]) if owner < 0],
        "layer0_activation_matches_all_arms": all(x[1]["activation"] == base[1]["activation"] for x in loaded.values()),
        "layer1_activation_matches_default_mirror": loaded["cpu_mirror"][2]["activation"] == base[2]["activation"],
        "layer1_activation_matches_gpu_profile": loaded["gpu_layer1"][2]["activation"] == base[2]["activation"],
        "absolute_position_or_token_key_in_route_record": False,
    },
    "combined_capture": {
        "rows": len(base[3]),
        "all_arms_have_same_position_token_keys": all(
            [(r["position"], r["token"]) for r in x[3]] ==
            [(r["position"], r["token"]) for r in base[3]] for x in loaded.values()),
        "first_position_token": [base[3][0]["position"], base[3][0]["token"]],
        "pairwise_ffn_y": {},
    },
    "persistent_state_fingerprints_equal": {
        "cpu_default_vs_cpu_mirror": base[4]["state"] == loaded["cpu_mirror"][4]["state"],
        "cpu_default_vs_gpu_profile": base[4]["state"] == loaded["gpu_layer1"][4]["state"],
        "cpu_mirror_vs_gpu_profile": loaded["cpu_mirror"][4]["state"] == loaded["gpu_layer1"][4]["state"],
    },
    "causal_isolation_proven": False,
    "limitation": "The GPU-profile arm changes the captured layer-1 input activation while the layer-0 route capture matches. The route records have no absolute position/token key. Combined output rows can be paired across arms, but cannot be joined to the selected route row; the intervention therefore does not isolate only the CPU/GPU execution of that layer-1 expert set.",
}

for left, right in (("cpu_default", "cpu_mirror"), ("cpu_default", "gpu_layer1"), ("cpu_mirror", "gpu_layer1")):
    a, b = loaded[left][3], loaded[right][3]
    if [(r["position"], r["token"]) for r in a] != [(r["position"], r["token"]) for r in b]:
        raise ValueError(f"combined row keys differ for {left} and {right}")
    summary["combined_capture"]["pairwise_ffn_y"][f"{left}_vs_{right}"] = delta(
        [r["ffn_y"] for r in a], [r["ffn_y"] for r in b])

out = HERE / "analysis.json"
out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
