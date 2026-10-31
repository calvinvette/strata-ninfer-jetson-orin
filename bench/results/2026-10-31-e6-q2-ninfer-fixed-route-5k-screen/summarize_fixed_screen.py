#!/usr/bin/env python3
"""Summarize a fixed-route Q2_0 backend screen without retaining response text."""

import argparse
import hashlib
import json
import random
import statistics
from pathlib import Path


def sha256_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def percentile(sorted_values, fraction):
    position = (len(sorted_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def arm(root, block, variant):
    directory = root / f"block-{block}-{variant}"
    requests = json.loads((directory / "requests.json").read_text())
    row = next(item for item in requests["checks"] if not item["warmup"])
    response = row["response"]
    text = response["choices"][0]["message"]["content"]
    usage = response["usage"]
    request_metrics = row["metrics_after"]["requests"][0]
    memory = [json.loads(line) for line in (directory / "memory.jsonl").read_text().splitlines() if line]
    cpus = [cpu["hz"] for sample in memory
            for cpu in sample.get("clock_observations", {}).get("cpu", {}).values()
            if cpu.get("hz")]
    gpus = [sample["clock_observations"]["gpu"]["hz"] for sample in memory
            if sample.get("clock_observations", {}).get("gpu", {}).get("hz")]
    oom = max((int(event.get("oom_kill", 0)) for sample in memory
               for cgroup in sample.get("cgroups", [])
               for event in [cgroup.get("memory_events", {})]), default=0)
    return {
        "status": row["status"],
        "cell": row["cell"],
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "answer_prefix_passed": text.startswith("NIMBUS-7319"),
        "response_sha256": sha256_text(text),
        "prompt_tps": request_metrics["prompt_tokens"] * 1000 / request_metrics["prompt_ms"],
        "decode_tps": request_metrics["engine_generated"] * 1000 / request_metrics["decode_ms"],
        "ttft_s": row["stream_observation"]["first_visible_delta_s"],
        "client_s": row["client_elapsed_s"],
        "gpu_hit_rate": request_metrics.get("hit_rate"),
        "minimum_available_bytes": min(sample["available_bytes"] for sample in memory),
        "maximum_swap_bytes": max(sample["swap_used_bytes"] for sample in memory),
        "oom_kill_max": oom,
        "cpu_hz_range": [min(cpus), max(cpus)] if cpus else None,
        "gpu_hz_range": [min(gpus), max(gpus)] if gpus else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screen_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    campaign = json.loads((args.screen_root / "campaign.json").read_text())
    blocks = sorted({row["block"] for row in campaign["runs"]})
    pairs = []
    for block in blocks:
        baseline, candidate = arm(args.screen_root, block, "baseline"), arm(args.screen_root, block, "candidate")
        if baseline["cell"] != candidate["cell"] or baseline["status"] != "pass" or candidate["status"] != "pass":
            raise ValueError(f"invalid paired request in block {block}")
        if baseline["prompt_tokens"] != 512 or candidate["prompt_tokens"] != 512:
            raise ValueError(f"unexpected prompt length in block {block}")
        if baseline["completion_tokens"] != 128 or candidate["completion_tokens"] != 128:
            raise ValueError(f"unexpected completion length in block {block}")
        pairs.append({"block": block, "baseline": baseline, "candidate": candidate})

    effects = {}
    rng = random.Random(20261031)
    for metric in ("prompt_tps", "decode_tps", "ttft_s", "client_s"):
        if metric.endswith("_tps"):
            ratios = [pair["candidate"][metric] / pair["baseline"][metric] - 1 for pair in pairs]
        else:
            ratios = [pair["baseline"][metric] / pair["candidate"][metric] - 1 for pair in pairs]
        samples = sorted(statistics.median(rng.choices(ratios, k=len(ratios)))
                         for _ in range(100000))
        effects[metric] = {
            "paired_effect_pct": [value * 100 for value in ratios],
            "median_effect_pct": statistics.median(ratios) * 100,
            "bootstrap_95_interval_pct": [percentile(samples, .025) * 100,
                                           percentile(samples, .975) * 100],
            "positive_favors": "NInfer",
        }

    all_arms = [pair[variant] for pair in pairs for variant in ("baseline", "candidate")]
    result = {
        "schema": 1,
        "experiment": "Q2_0 route-ranked fixed 5K-resident Strata vs strict NInfer API screen",
        "pair_count": len(pairs),
        "campaign": campaign,
        "pairs": pairs,
        "arm_medians": {
            variant: {metric: statistics.median(pair[variant][metric] for pair in pairs)
                      for metric in ("prompt_tps", "decode_tps", "ttft_s", "client_s", "gpu_hit_rate")}
            for variant in ("baseline", "candidate")
        },
        "paired_effects": effects,
        "quality_summary": {
            "all_passed": all(row["status"] == "pass" for row in all_arms),
            "all_exact_prefixes": all(row["answer_prefix_passed"] for row in all_arms),
            "all_128_token_outputs": all(row["completion_tokens"] == 128 for row in all_arms),
            "one_shared_response_hash": len({row["response_sha256"] for row in all_arms}) == 1,
        },
        "resource_summary": {
            "minimum_available_bytes": min(row["minimum_available_bytes"] for row in all_arms),
            "maximum_swap_bytes": max(row["maximum_swap_bytes"] for row in all_arms),
            "maximum_oom_kill_counter": max(row["oom_kill_max"] for row in all_arms),
            "cpu_hz_range": [min(row["cpu_hz_range"][0] for row in all_arms if row["cpu_hz_range"]),
                             max(row["cpu_hz_range"][1] for row in all_arms if row["cpu_hz_range"])],
            "gpu_hz_range": [min(row["gpu_hz_range"][0] for row in all_arms if row["gpu_hz_range"]),
                             max(row["gpu_hz_range"][1] for row in all_arms if row["gpu_hz_range"])],
            "emc_clock_observed": False,
            "energy_measured": False,
        },
        "scope": "three-pair screen with a fixed 5000-slot profile ranked from this workload's prior routing trace; oracle-residency diagnostic, not a deployable profile or broad quality claim",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"arm_medians": result["arm_medians"], "paired_effects": effects,
                      "quality_summary": result["quality_summary"],
                      "resource_summary": result["resource_summary"]}, indent=2))


if __name__ == "__main__":
    main()
