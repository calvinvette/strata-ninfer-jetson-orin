#!/usr/bin/env python3
"""Validate and summarize a paired E6 ledger aggregation screen."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from summarize_controls import interval, metrics  # noqa: E402


BACKEND_ARGS = ("--expert-backend", "ninfer", "--expert-backend-strict")
CONFIG_LABEL_FIELDS = {"model_name", "port", "log"}
METRICS = ("prompt_tps", "decode_tps", "client_ttft_s", "client_total_s")


def config_for_comparison(config: dict) -> dict:
    normalized = copy.deepcopy(config)
    args = normalized["args"]
    if "--expert-backend" in args:
        at = args.index("--expert-backend")
        if args[at:at + 2] != ["--expert-backend", "ninfer"]:
            raise ValueError("candidate backend selector is not strict NInfer")
        del args[at:at + 2]
        args.remove("--expert-backend-strict")
    for key in CONFIG_LABEL_FIELDS:
        normalized.pop(key, None)
    return normalized


def response_message(row: dict) -> dict:
    return row["response"]["choices"][0]["message"]


def observed_clock_ranges(samples: list[dict]) -> dict:
    cpu = [entry["hz"] / 1e6 for sample in samples
           for entry in sample.get("clock_observations", {}).get("cpu", {}).values()
           if isinstance(entry, dict) and isinstance(entry.get("hz"), (int, float))]
    gpu = [entry["hz"] / 1e6 for sample in samples
           if isinstance((entry := sample.get("clock_observations", {}).get("gpu")), dict)
           and isinstance(entry.get("hz"), (int, float))]
    emc = [entry["hz"] / 1e6 for sample in samples
           if isinstance((entry := sample.get("clock_observations", {}).get("emc")), dict)
           and isinstance(entry.get("hz"), (int, float))]

    def bounds(values):
        return {"minimum_mhz": min(values), "maximum_mhz": max(values)} if values else None

    return {"cpu": bounds(cpu), "gpu": bounds(gpu),
            "emc": bounds(emc) or {"status": "unavailable"}}


def summarize(campaign: Path, quality_dir: Path, fixture_path: Path) -> dict:
    plan = json.loads((campaign / "campaign.json").read_text())
    if len(plan.get("runs", [])) != 6 or any(run.get("status") != "pass" for run in plan["runs"]):
        raise ValueError("expected six terminal passing process arms")
    if len({run["block"] for run in plan["runs"]}) != 3:
        raise ValueError("expected three independent paired blocks")

    fixture = json.loads(fixture_path.read_text())
    if len(fixture.get("workloads", [])) != 1:
        raise ValueError("expected one ledger workload")
    workload = fixture["workloads"][0]
    if (workload.get("cell") != "heldout-ledger-aggregation-2048" or
            workload.get("prompt_tokens") != 2048 or workload.get("generate_tokens") != 256 or
            workload.get("allow_natural_stop") is not True):
        raise ValueError("fixture does not match the qualified ledger workload")
    fixture_hash = hashlib.sha256(fixture_path.read_bytes()).hexdigest()

    paired = []
    for block in range(3):
        arms, configs, quality = {}, {}, {}
        for variant in ("baseline", "candidate"):
            name = f"block-{block}-{variant}"
            directory = campaign / name
            arms[variant] = json.loads((directory / "requests.json").read_text())
            configs[variant] = json.loads((directory / "server-config.json").read_text())
            quality_path = quality_dir / f"block-{block}-{variant}-quality.json"
            quality[variant] = json.loads(quality_path.read_text())
            if not quality[variant].get("all_passed"):
                raise ValueError(f"independent quality oracle failed: {quality_path}")
            if len(quality[variant].get("outcomes", [])) != 2:
                raise ValueError(f"expected warmup and measured oracle outcomes: {quality_path}")
        if config_for_comparison(configs["baseline"]) != config_for_comparison(configs["candidate"]):
            raise ValueError(f"paired launch configuration differs beyond backend selector in block {block}")

        rows = {}
        for variant in ("baseline", "candidate"):
            checks = arms[variant].get("checks", [])
            if len(checks) != 2 or any(row.get("status") != "pass" for row in checks):
                raise ValueError(f"API workload failed in block {block} {variant}")
            warmup = next((row for row in checks if row.get("warmup")), None)
            measured = next((row for row in checks if not row.get("warmup")), None)
            if warmup is None or measured is None:
                raise ValueError(f"missing warmup or measured request in block {block} {variant}")
            if any(row.get("cell") != workload["cell"] or
                   row.get("response", {}).get("usage", {}).get("prompt_tokens") != 2048
                   for row in checks):
                raise ValueError(f"actual prompt cell mismatch in block {block} {variant}")
            rows[variant] = measured
        messages_match = response_message(rows["baseline"]) == response_message(rows["candidate"])
        if not messages_match:
            raise ValueError(f"paired API responses differ in block {block}")

        pair = {"block": block, "api_responses_identical": messages_match, "arms": {}}
        for variant in ("baseline", "candidate"):
            observed = metrics(rows[variant])
            quality_outcomes = quality[variant]["outcomes"]
            pair["arms"][variant] = {
                "metrics": {key: observed[key] for key in METRICS},
                "completion_tokens": observed["completion_tokens"],
                "expert_cache_hit_rate": observed["cache_hit_rate"],
                "answer_sha256": quality_outcomes[1]["answer_sha256"],
            }

        # The process supervisor's samples provide resource-floor and clock evidence.
        for variant in ("baseline", "candidate"):
            directory = campaign / f"block-{block}-{variant}"
            supervised = json.loads((directory / "result.json").read_text())
            samples = [json.loads(line) for line in (directory / "memory.jsonl").read_text().splitlines()]
            if not samples:
                raise ValueError(f"missing memory samples in block {block} {variant}")
            cgroup_oom = [entry.get("memory_events", {}).get("oom_kill", 0)
                          for sample in samples for entry in sample.get("cgroups", [])]
            swap_peak = max(sample.get("swap_used_bytes", 0) for sample in samples)
            pair["arms"][variant]["resources"] = {
                "minimum_available_gib": supervised["minimum_available_bytes"] / 1024**3,
                "minimum_admission_available_gib": supervised["minimum_admission_available_bytes"] / 1024**3,
                "maximum_swap_used_gib": swap_peak / 1024**3,
                "maximum_oom_kill_counter": max(cgroup_oom, default=0),
                "clocks": observed_clock_ranges(samples),
            }
        paired.append(pair)

    summary = {}
    for key in METRICS:
        baseline = [pair["arms"]["baseline"]["metrics"][key] for pair in paired]
        candidate = [pair["arms"]["candidate"]["metrics"][key] for pair in paired]
        ratios = [b / a for a, b in zip(baseline, candidate)]
        summary[key] = {
            "baseline_median": statistics.median(baseline),
            "candidate_median": statistics.median(candidate),
            "median_within_block_candidate_over_baseline": statistics.median(ratios),
            "paired_bootstrap_95_interval": interval(ratios),
        }

    resource_rows = [arm["resources"] for pair in paired for arm in pair["arms"].values()]
    cpu_ranges = [row["clocks"]["cpu"] for row in resource_rows if row["clocks"]["cpu"]]
    gpu_ranges = [row["clocks"]["gpu"] for row in resource_rows if row["clocks"]["gpu"]]

    def combine_ranges(rows):
        return {"minimum_mhz": min(row["minimum_mhz"] for row in rows),
                "maximum_mhz": max(row["maximum_mhz"] for row in rows)} if rows else None

    return {
        "cell": workload["cell"],
        "paired_blocks": len(paired),
        "api_content_matching_blocks": sum(pair["api_responses_identical"] for pair in paired),
        **summary,
        "fixture_sha256": fixture_hash,
        "prompt_tokens": workload["prompt_tokens"],
        "generate_token_limit": workload["generate_tokens"],
        "allow_natural_stop": workload["allow_natural_stop"],
        "resources": {
            "minimum_available_gib": min(row["minimum_available_gib"] for row in resource_rows),
            "minimum_admission_available_gib": min(row["minimum_admission_available_gib"] for row in resource_rows),
            "maximum_swap_used_gib": max(row["maximum_swap_used_gib"] for row in resource_rows),
            "maximum_oom_kill_counter": max(row["maximum_oom_kill_counter"] for row in resource_rows),
            "cpu_clock_mhz_range": combine_ranges(cpu_ranges),
            "gpu_clock_mhz_range": combine_ranges(gpu_ranges),
            "emc_clock": "not available: permission denied",
            "energy": "instantaneous tegrastats rail samples were captured; energy was not analyzed or used for qualification",
        },
        "pairs": paired,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--quality-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.campaign, args.quality_dir, args.fixture)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("cell", "paired_blocks", "api_content_matching_blocks", "decode_tps")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
