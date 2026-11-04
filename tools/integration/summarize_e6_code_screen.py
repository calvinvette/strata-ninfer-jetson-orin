#!/usr/bin/env python3
"""Validate and summarize paired E6 executable code-task backend screens."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from evaluate_e6_code_task import evaluate  # noqa: E402
from summarize_controls import interval, metrics  # noqa: E402
from summarize_e6_ledger_screen import observed_clock_ranges  # noqa: E402

METRICS = ("prompt_tps", "decode_tps", "client_ttft_s", "client_total_s")
BACKEND_FLAGS = ("--expert-backend", "ninfer", "--expert-backend-strict")
LABEL_FIELDS = {"model_name", "port", "log"}


def config_for_comparison(config: dict) -> dict:
    normalized = copy.deepcopy(config)
    args = normalized["args"]
    if "--expert-backend" in args:
        index = args.index("--expert-backend")
        if args[index:index + 2] != ["--expert-backend", "ninfer"]:
            raise ValueError("candidate backend selector is not strict NInfer")
        del args[index:index + 2]
        args.remove("--expert-backend-strict")
    for key in LABEL_FIELDS:
        normalized.pop(key, None)
    return normalized


def quality_for_requests(requests: dict, expected_cell: str, expected_prompt: int) -> dict:
    outcomes = []
    for row in requests.get("checks", []):
        passed = row.get("status") == "pass"
        response = row.get("response") or {}
        if (row.get("cell") != expected_cell or
                response.get("usage", {}).get("prompt_tokens") != expected_prompt):
            passed = False
            outcomes.append({"warmup": row.get("warmup"), "passed": False,
                             "error": "cell or actual prompt-token count mismatch"})
            continue
        text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            outcomes.append({"warmup": row.get("warmup"), **evaluate(text)})
        except Exception as exc:
            outcomes.append({"warmup": row.get("warmup"), "passed": False,
                             "error": f"{type(exc).__name__}: {exc}"})
    return {"outcomes": outcomes,
            "all_passed": len(outcomes) == 2 and all(x.get("passed") for x in outcomes)}


def expert_hit_rate(engine_log: Path) -> float:
    matches = re.findall(r"decode expert cache hit rate: ([0-9.]+)%", engine_log.read_text())
    if not matches:
        raise ValueError(f"missing per-request expert-cache hit rate in {engine_log}")
    return float(matches[-1]) / 100


def summarize(campaign: Path, fixture_path: Path) -> dict:
    plan = json.loads((campaign / "campaign.json").read_text())
    if len(plan.get("runs", [])) != 6 or any(run.get("status") != "pass" for run in plan["runs"]):
        raise ValueError("expected six terminal passing process arms")
    if len({run["block"] for run in plan["runs"]}) != 3:
        raise ValueError("expected three independent paired blocks")
    fixture = json.loads(fixture_path.read_text())
    if len(fixture.get("workloads", [])) != 1:
        raise ValueError("expected one code task")
    workload = fixture["workloads"][0]
    cell, prompt_tokens = workload.get("cell"), workload.get("prompt_tokens")
    if not isinstance(cell, str) or not isinstance(prompt_tokens, int):
        raise ValueError("code fixture lacks cell or exact prompt-token count")

    paired = []
    for block in range(3):
        arms, configs = {}, {}
        for variant in ("baseline", "candidate"):
            directory = campaign / f"block-{block}-{variant}"
            arms[variant] = json.loads((directory / "requests.json").read_text())
            configs[variant] = json.loads((directory / "server-config.json").read_text())
        if config_for_comparison(configs["baseline"]) != config_for_comparison(configs["candidate"]):
            raise ValueError(f"paired launch configuration differs beyond backend selector in block {block}")

        rows, qualities = {}, {}
        for variant in ("baseline", "candidate"):
            checks = arms[variant].get("checks", [])
            if len(checks) != 2 or any(row.get("status") != "pass" for row in checks):
                raise ValueError(f"API workload failed in block {block} {variant}")
            if {bool(row.get("warmup")) for row in checks} != {False, True}:
                raise ValueError(f"missing warmup or measured request in block {block} {variant}")
            qualities[variant] = quality_for_requests(arms[variant], cell, prompt_tokens)
            if not qualities[variant]["all_passed"]:
                raise ValueError(f"independent executable oracle failed in block {block} {variant}")
            rows[variant] = next(row for row in checks if not row.get("warmup"))
        response_same = rows["baseline"]["response"]["choices"][0]["message"] == rows["candidate"]["response"]["choices"][0]["message"]
        if not response_same:
            raise ValueError(f"paired API responses differ in block {block}")

        pair = {"block": block, "api_responses_identical": response_same, "arms": {}}
        for variant in ("baseline", "candidate"):
            observation = metrics(rows[variant])
            hit_rate = expert_hit_rate(campaign / f"block-{block}-{variant}" / "engine.log")
            pair["arms"][variant] = {
                "metrics": {key: observation[key] for key in METRICS},
                "prompt_tokens": observation["prompt_tokens"],
                "completion_tokens": observation["completion_tokens"],
                "drafts_offered": observation["drafted"],
                "drafts_accepted": observation["accepted"],
                "expert_cache_hit_rate": hit_rate,
                "answer_sha256": qualities[variant]["outcomes"][1]["code_sha256"],
            }
            directory = campaign / f"block-{block}-{variant}"
            supervised = json.loads((directory / "result.json").read_text())
            samples = [json.loads(line) for line in (directory / "memory.jsonl").read_text().splitlines()]
            oom = [entry.get("memory_events", {}).get("oom_kill", 0)
                   for sample in samples for entry in sample.get("cgroups", [])]
            pair["arms"][variant]["resources"] = {
                "minimum_available_gib": supervised["minimum_available_bytes"] / 1024**3,
                "minimum_admission_available_gib": supervised["minimum_admission_available_bytes"] / 1024**3,
                "maximum_swap_used_gib": max(sample.get("swap_used_bytes", 0) for sample in samples) / 1024**3,
                "maximum_oom_kill_counter": max(oom, default=0),
                "clocks": observed_clock_ranges(samples),
            }
        for field in ("prompt_tokens", "completion_tokens"):
            if pair["arms"]["baseline"][field] != pair["arms"]["candidate"][field]:
                raise ValueError(f"actual paired workload mismatch in block {block}: {field}")
        paired.append(pair)

    effects = {}
    for key in METRICS:
        baseline = [pair["arms"]["baseline"]["metrics"][key] for pair in paired]
        candidate = [pair["arms"]["candidate"]["metrics"][key] for pair in paired]
        ratios = [b / a for a, b in zip(baseline, candidate)]
        effects[key] = {
            "baseline_median": statistics.median(baseline),
            "candidate_median": statistics.median(candidate),
            "median_within_block_candidate_over_baseline": statistics.median(ratios),
            "paired_bootstrap_95_interval": interval(ratios),
        }
    resource_rows = [arm["resources"] for pair in paired for arm in pair["arms"].values()]
    cpu = [r["clocks"]["cpu"] for r in resource_rows if r["clocks"]["cpu"]]
    gpu = [r["clocks"]["gpu"] for r in resource_rows if r["clocks"]["gpu"]]

    def bounds(rows):
        return {"minimum_mhz": min(x["minimum_mhz"] for x in rows),
                "maximum_mhz": max(x["maximum_mhz"] for x in rows)} if rows else None

    return {
        "cell": cell, "paired_blocks": len(paired),
        "api_content_matching_blocks": sum(row["api_responses_identical"] for row in paired),
        **effects,
        "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "prompt_tokens": prompt_tokens,
        "generate_token_limit": workload.get("generate_tokens"),
        "allow_natural_stop": workload.get("allow_natural_stop", False),
        "resources": {
            "minimum_available_gib": min(row["minimum_available_gib"] for row in resource_rows),
            "minimum_admission_available_gib": min(row["minimum_admission_available_gib"] for row in resource_rows),
            "maximum_swap_used_gib": max(row["maximum_swap_used_gib"] for row in resource_rows),
            "maximum_oom_kill_counter": max(row["maximum_oom_kill_counter"] for row in resource_rows),
            "cpu_clock_mhz_range": bounds(cpu), "gpu_clock_mhz_range": bounds(gpu),
            "emc_clock": "unavailable: permission denied",
            "energy": "rail samples captured; energy was not integrated or used for qualification",
        },
        "pairs": paired,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.campaign, args.fixture)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("cell", "paired_blocks", "api_content_matching_blocks", "decode_tps")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
