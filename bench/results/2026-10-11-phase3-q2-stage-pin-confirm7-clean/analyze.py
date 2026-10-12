#!/usr/bin/env python3
"""Summarize the seven independent, warmup-separated Q2_0 staging pairs."""
import json
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METRICS = ("prompt_ms", "decode_ms", "request_ms")
PATTERN = re.compile(
    r"prompt 512 tokens = .*? in (\d+) ms .*?, 64 generated in (\d+) ms"
)


def percentile(sorted_values, p):
    return sorted_values[round((len(sorted_values) - 1) * p)]


def main():
    pairs = []
    arm_samples = {"pinned": {m: [] for m in METRICS},
                   "pageable": {m: [] for m in METRICS}}
    min_host_available = None
    min_cgroup_headroom = None
    max_oom = 0
    warmup_completion_match_pairs = 0
    for i in range(7):
        pair_dir = ROOT / f"pair-{i:02d}"
        result = json.loads((pair_dir / "experiment/results.json").read_text())
        supervisor = json.loads((pair_dir / "supervisor/result.json").read_text())
        assert result["passed"] and supervisor["status"] == "pass"
        assert result["prompt_tokens"] == 512 and result["generated_tokens"] == 64
        assert result["warmup_prompt_tokens"] == 172
        assert result["warmup_generated_tokens"] == 64
        assert len({a["warmup"]["prompt_sha256"] for a in result["arms"]}) == 1
        assert all(a["warmup"]["generated_tokens"] == 64 for a in result["arms"])
        if len({a["warmup"]["ids_sha256"] for a in result["arms"]}) == 1:
            warmup_completion_match_pairs += 1
        assert result["pair_comparisons"][0]["token_ids_equal"]
        for arm in result["arms"]:
            log = (pair_dir / f"experiment/pair-0-{arm['name']}.log").read_text()
            measured = [tuple(map(int, m)) for m in PATTERN.findall(log)]
            if not measured:
                raise RuntimeError(f"missing measured request in pair {i} {arm['name']}")
            prompt, decode = measured[-1]
            arm_samples[arm["name"]]["prompt_ms"].append(prompt)
            arm_samples[arm["name"]]["decode_ms"].append(decode)
            arm_samples[arm["name"]]["request_ms"].append(prompt + decode)
        effects = result["pair_comparisons"][0]["paired_pinned_minus_pageable_pct"]
        pairs.append(effects)
        available_host = supervisor["minimum_available_bytes"]
        min_host_available = (available_host if min_host_available is None
                              else min(min_host_available, available_host))
        for line in (pair_dir / "supervisor/memory.jsonl").read_text().splitlines():
            sample = json.loads(line)
            for cg in sample.get("cgroups", []):
                if "/run-" in cg["path"] and cg.get("max_bytes"):
                    available = cg["max_bytes"] - cg["current_bytes"]
                    min_cgroup_headroom = (available if min_cgroup_headroom is None
                                           else min(min_cgroup_headroom, available))
                max_oom = max(max_oom, cg.get("memory_events", {}).get("oom", 0))
                max_oom = max(max_oom, cg.get("memory_events", {}).get("oom_kill", 0))

    output = {
        "pairs": len(pairs),
        "warmup_completion_match_pairs": warmup_completion_match_pairs,
        "paired_delta_definition": "100 * (pinned - pageable) / pageable; positive means pinned slower",
        "paired_effects_pct": {},
        "arm_medians_ms": {},
        "minimum_host_available_bytes": min_host_available,
        "minimum_28g_cgroup_headroom_bytes": min_cgroup_headroom,
        "max_oom_or_oom_kill_counter": max_oom,
    }
    for arm, metrics in arm_samples.items():
        output["arm_medians_ms"][arm] = {
            metric: statistics.median(values) for metric, values in metrics.items()
        }
    for metric in METRICS:
        values = [p[metric] for p in pairs]
        rng = random.Random(20261011 + len(metric))
        boot = sorted(statistics.median(rng.choices(values, k=len(values)))
                      for _ in range(200_000))
        output["paired_effects_pct"][metric] = {
            "median": statistics.median(values),
            "percentile_bootstrap_95": [percentile(boot, .025), percentile(boot, .975)],
            "pair_deltas": values,
            "bootstrap_resamples": len(boot),
        }
    (ROOT / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
