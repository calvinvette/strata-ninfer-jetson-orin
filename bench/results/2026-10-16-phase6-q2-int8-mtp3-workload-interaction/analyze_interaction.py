#!/usr/bin/env python3
"""Validate and analyze paired MTP-by-workload interaction campaigns."""
import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval, metrics

HERE = Path(__file__).resolve().parent
GIB = 1024 ** 3
WORKLOAD_FILES = {
    "screen": {"short": "workload-short.json", "near_limit": "workload-near-limit.json"},
    "confirm": {"short": "confirmation/workload-short.json",
                "near_limit": "confirmation/workload-near-limit.json"},
}


def percentile(values, p):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


def interaction_interval(short_ratios, long_ratios, seed):
    rng = random.Random(seed)
    draws = []
    for _ in range(5000):
        short = statistics.median(rng.choices(short_ratios, k=len(short_ratios)))
        long = statistics.median(rng.choices(long_ratios, k=len(long_ratios)))
        draws.append(long / short)
    draws.sort()
    return [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))]]


def read_json(path):
    return json.loads(path.read_text())


def marker_check(content, expected):
    positions = [content.find(code) for code in expected["expected_codes"]]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        return False, "missing or out-of-order retrieval marker"
    if any(content.count(code) != 1 for code in expected["expected_codes"]):
        return False, "retrieval marker did not occur exactly once"
    if "expected_suffix_sum" in expected:
        match = re.search(r"\bSUM\s*=\s*(\d+)\b", content)
        if not match or int(match.group(1)) != expected["expected_suffix_sum"]:
            return False, "independent suffix-sum oracle mismatch"
    return True, "exact markers and task oracle passed"


def load_observation(campaign_root, run, expected, expected_binary):
    directory = ROOT / run["output_dir"]
    supervisor_path = directory / "result.json"
    requests_path = directory / "requests.json"
    memory_path = directory / "memory.jsonl"
    tegrastats_path = directory / "tegrastats.txt"
    if not all(path.is_file() for path in (supervisor_path, requests_path, memory_path, tegrastats_path)):
        return None, "missing supervisor, request or memory artifact"
    supervisor = read_json(supervisor_path)
    if run.get("status") != "pass" or supervisor.get("status") != "pass" or supervisor.get("returncode") != 0:
        return None, "campaign arm or supervisor did not pass"
    if run.get("binary_sha256_after") != expected_binary:
        return None, "binary identity changed during campaign"
    requests = read_json(requests_path)
    measured = [row for row in requests.get("checks", []) if not row.get("warmup")]
    if len(measured) != 1:
        return None, "expected exactly one measured request"
    row = measured[0]
    if row.get("status") != "pass":
        return None, f"request failed: {row.get('reason')}"
    usage = row.get("response", {}).get("usage", {})
    if usage.get("prompt_tokens") != expected["prompt_tokens"]:
        return None, "formatted prompt token count mismatch"
    answer = row.get("response", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
    passed, reason = marker_check(answer, expected)
    if not passed:
        return None, reason
    try:
        observed_metrics = metrics(row)
    except (KeyError, ValueError, TypeError, ZeroDivisionError) as error:
        return None, f"invalid request timing counters: {error}"
    if observed_metrics["prompt_tokens"] != expected["prompt_tokens"]:
        return None, "engine and API prompt counts differ"

    memory = [json.loads(line) for line in memory_path.read_text().splitlines() if line.strip()]
    if not memory:
        return None, "empty memory telemetry"
    selected = [sample for sample in memory
                if row["request_start_monotonic_s"] <= sample["monotonic_s"] <= row["request_end_monotonic_s"]]
    if not selected:
        return None, "no memory sample overlaps measured request"
    cgroup_events = {}
    cgroup_peak = 0
    for sample in memory:
        for group in sample.get("cgroups", []):
            cgroup_peak = max(cgroup_peak, group.get("current_bytes", 0))
            for name, count in group.get("memory_events", {}).items():
                cgroup_events[name] = max(cgroup_events.get(name, 0), count)
    event_failures = {key: value for key, value in cgroup_events.items()
                      if key in ("high", "max", "oom", "oom_kill", "oom_group_kill") and value}
    if event_failures:
        return None, f"cgroup pressure/OOM events: {event_failures}"
    if min(sample["available_bytes"] for sample in memory) < 6 * GIB:
        return None, "six-GiB physical availability floor breached"

    engine = row.get("metrics_after", {}).get("engine", {})
    observed_metrics.update(
        answer=answer,
        quality=reason,
        actual_kv=engine.get("kv"),
        actual_expert_slots=engine.get("expert_slots"),
        actual_mtp_max=engine.get("mtp_max"),
        min_host_gib=min(sample["available_bytes"] for sample in memory) / GIB,
        min_request_host_gib=min(sample["available_bytes"] for sample in selected) / GIB,
        min_admission_gib=min(sample["admission_available_bytes"] for sample in memory) / GIB,
        max_scope_gib=cgroup_peak / GIB,
        max_swap_gib=max(sample["swap_used_bytes"] for sample in memory) / GIB,
        cgroup_events=cgroup_events,
    )
    clocks = [sample.get("clock_observations", {}) for sample in selected]
    gpu = [clock.get("gpu", {}).get("hz") for clock in clocks
           if isinstance(clock.get("gpu", {}).get("hz"), (int, float))]
    cpu = [hz for clock in clocks for row_cpu in clock.get("cpu", {}).values()
           if isinstance((hz := row_cpu.get("hz")), (int, float))]
    observed_metrics["gpu_clock_mhz_range"] = ([min(gpu) / 1e6, max(gpu) / 1e6] if gpu else None)
    observed_metrics["cpu_clock_mhz_range"] = ([min(cpu) / 1e6, max(cpu) / 1e6] if cpu else None)

    first = memory[0]
    offset = first["wall_time_s"] - first["monotonic_s"]
    window_start = row["request_start_monotonic_s"] + offset
    window_end = row["request_end_monotonic_s"] + offset
    tegrastats_lines = tegrastats_path.read_text(errors="replace").splitlines()
    temperatures = []
    emc_states = set()
    for line in tegrastats_lines:
        try:
            timestamp = datetime.strptime(line[:19], "%m-%d-%Y %H:%M:%S").timestamp()
        except ValueError:
            continue
        if window_start <= timestamp <= window_end:
            match = re.search(r"\btj@([\d.]+)C", line)
            if match:
                temperatures.append(float(match.group(1)))
    for clock in clocks:
        emc = clock.get("emc", {})
        emc_states.add("available" if isinstance(emc.get("hz"), (int, float))
                       else emc.get("status", "missing"))
    observed_metrics["tj_range_c"] = ([min(temperatures), max(temperatures)] if temperatures else None)
    observed_metrics["emc_observation_status"] = sorted(emc_states)
    rails = rails_from_lines(tegrastats_lines)
    observed_metrics["named_rail_energy"] = window_energy(
        rails, window_start, window_end)
    return observed_metrics, None


def bootstrap_summary(ratios, seed):
    return {
        "paired_blocks": len(ratios),
        "median_candidate_over_baseline_ratio": statistics.median(ratios),
        "median_paired_change_percent": (statistics.median(ratios) - 1) * 100,
        "paired_bootstrap_95_interval_percent": [(x - 1) * 100 for x in interval(ratios, seed)],
        "block_ratios": ratios,
    }


def summarize_workload(pairs, workload, seed):
    rows = [pair for pair in pairs if pair["workload"] == workload]
    fields = ("prompt_tps", "decode_tps", "client_ttft_s", "client_total_s")
    result = {"workload": workload, "paired_blocks": len(rows), "metrics": {}}
    for field_index, field in enumerate(fields):
        ratios = [row["candidate"][field] / row["baseline"][field] for row in rows]
        result["metrics"][field] = {
            **bootstrap_summary(ratios, seed + field_index),
            "baseline_median": statistics.median(row["baseline"][field] for row in rows),
            "candidate_median": statistics.median(row["candidate"][field] for row in rows),
            "baseline_empirical_p95_nearest_rank": percentile([row["baseline"][field] for row in rows], 0.95),
            "candidate_empirical_p95_nearest_rank": percentile([row["candidate"][field] for row in rows], 0.95),
            "p95_sample_count_per_arm": len(rows),
        }
    result["mtp"] = {
        "drafted_per_candidate_request": [row["candidate"]["drafted"] for row in rows],
        "accepted_per_candidate_request": [row["candidate"]["accepted"] for row in rows],
    }
    result["resources"] = {
        "minimum_host_gib": min(min(row[arm]["min_host_gib"] for row in rows)
                                 for arm in ("baseline", "candidate")),
        "minimum_admission_gib": min(min(row[arm]["min_admission_gib"] for row in rows)
                                      for arm in ("baseline", "candidate")),
        "maximum_scope_gib": max(max(row[arm]["max_scope_gib"] for row in rows)
                                 for arm in ("baseline", "candidate")),
    }
    return result


def summarize_interaction(summaries, seed):
    by_workload = {row["workload"]: row for row in summaries}
    fields = ("prompt_tps", "decode_tps", "client_ttft_s", "client_total_s")
    result = {}
    for field in fields:
        short = by_workload["short"]["metrics"][field]["block_ratios"]
        long = by_workload["near_limit"]["metrics"][field]["block_ratios"]
        point = statistics.median(long) / statistics.median(short)
        result[field] = {
            "long_over_short_ratio_of_MTP_candidate_baseline_effect": point,
            "interaction_percent": (point - 1) * 100,
            "independent_paired_process_bootstrap_95_interval_ratio": interaction_interval(short, long, seed),
            "interpretation": "ratio greater than 1 means the candidate/baseline response ratio is higher at 7,501 tokens than at 512 tokens",
        }
    return result


def analyze(campaign_root):
    campaign = read_json(campaign_root / "campaign.json")
    workload_files = WORKLOAD_FILES[campaign["suite"]]
    workloads = {name: read_json(HERE / path)["workloads"][0]
                 for name, path in workload_files.items()}
    expected_runs = 4 * campaign["repetitions_per_workload"]
    errors = []
    if len(campaign.get("runs", [])) != expected_runs:
        errors.append(f"expected {expected_runs} run records, found {len(campaign.get('runs', []))}")
    if campaign.get("status") != "pass":
        errors.append(f"campaign status is {campaign.get('status')}")
    pairs = {}
    rejected = []
    for run in campaign.get("runs", []):
        key = (run.get("workload"), run.get("replicate"))
        observation, reason = load_observation(campaign_root, run, workloads.get(run.get("workload"), {}), campaign.get("binary_sha256"))
        if observation is None:
            rejected.append({"workload": key[0], "replicate": key[1],
                             "variant": run.get("variant"), "reason": reason})
        else:
            pairs.setdefault(key, {})[run["variant"]] = observation
    complete_pairs = []
    for (workload, replicate), arms in sorted(pairs.items()):
        if set(arms) != {"baseline", "candidate"}:
            rejected.append({"workload": workload, "replicate": replicate,
                             "reason": "pair has a missing or failed arm"})
            continue
        if arms["baseline"]["answer"] != arms["candidate"]["answer"]:
            rejected.append({"workload": workload, "replicate": replicate,
                             "reason": "same-pair answer text differs"})
            continue
        if arms["baseline"]["actual_kv"] != "int8" or arms["candidate"]["actual_kv"] != "int8":
            rejected.append({"workload": workload, "replicate": replicate,
                             "reason": "actual KV format is not int8"})
            continue
        if arms["baseline"]["actual_mtp_max"] != 0 or arms["candidate"]["actual_mtp_max"] != 3:
            rejected.append({"workload": workload, "replicate": replicate,
                             "reason": "actual MTP window differs from planned off/3 factors"})
            continue
        if arms["baseline"]["actual_expert_slots"] != arms["candidate"]["actual_expert_slots"]:
            rejected.append({"workload": workload, "replicate": replicate,
                             "reason": "actual expert-cache capacity differs within pair"})
            continue
        complete_pairs.append({"workload": workload, "replicate": replicate,
                               "baseline": arms["baseline"], "candidate": arms["candidate"]})
    summaries = [summarize_workload(complete_pairs, workload, 870126 + index * 100)
                 for index, workload in enumerate(("short", "near_limit"))
                 if any(row["workload"] == workload for row in complete_pairs)]
    summary_workloads = {row["workload"] for row in summaries}
    interaction = (summarize_interaction(summaries, 870526)
                   if summary_workloads == {"short", "near_limit"} else None)
    expected_per_workload = campaign["repetitions_per_workload"]
    passed = (not errors and not rejected and all(row["paired_blocks"] == expected_per_workload
                                                   for row in summaries)
              and interaction is not None)
    return {
        "scope": campaign.get("scope"),
        "suite": campaign.get("suite"),
        "status": "pass" if passed else "incomplete_or_failed",
        "binary_sha256": campaign.get("binary_sha256"),
        "binary_source_commit": campaign.get("binary_source_commit"),
        "uncertainty": "bootstrap samples whole independent paired fresh-service runs; workload strata resampled independently",
        "interaction_transform": "log candidate/baseline response ratios; difference of workload medians, exponentiated",
        "workload_summaries": summaries,
        "interaction": interaction,
        "complete_pair_count": len(complete_pairs),
        "errors": errors,
        "rejected_cells": rejected,
        "paired_observations": complete_pairs,
        "limitations": [
            "two prompt lengths and one Q2_0 int8-KV profile do not define a general response surface",
            "dynamic clocks and background activity remain visible; named rail estimates are board diagnostics, not request-attributed energy",
            "empirical p95 with seven requests per arm is descriptive and has low tail resolution",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.campaign)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    with args.output.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["workload", "metric", "paired_blocks", "baseline_median",
                         "candidate_median", "paired_change_percent", "ci_low_percent",
                         "ci_high_percent", "interaction_ratio", "interaction_ci_low_ratio",
                         "interaction_ci_high_ratio"])
        interactions = result.get("interaction") or {}
        for workload_row in result["workload_summaries"]:
            workload = workload_row["workload"]
            for metric_name, values in workload_row["metrics"].items():
                interaction = interactions.get(metric_name, {})
                ci = values["paired_bootstrap_95_interval_percent"]
                ici = interaction.get("independent_paired_process_bootstrap_95_interval_ratio", [None, None])
                writer.writerow([workload, metric_name, values["paired_blocks"],
                                 values["baseline_median"], values["candidate_median"],
                                 values["median_paired_change_percent"], ci[0], ci[1],
                                 interaction.get("long_over_short_ratio_of_MTP_candidate_baseline_effect"),
                                 ici[0], ici[1]])
    print(json.dumps({"status": result["status"], "complete_pair_count": result["complete_pair_count"],
                      "rejected_cells": len(result["rejected_cells"]),
                      "interaction": result["interaction"]}, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
