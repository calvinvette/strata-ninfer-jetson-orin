#!/usr/bin/env python3
"""Produce a sanitized summary from an E6 adaptive 5K backend screen."""

import argparse
import hashlib
import json
import random
import re
import statistics
from pathlib import Path


CELL = "e6-heldout-retrieval-1-pp512-tg128"


def read_arm(root, pair, arm):
    path = root / f"pair-{pair}-{arm}"
    requests = json.loads((path / "requests.json").read_text())
    check = next(row for row in requests["checks"]
                 if row.get("cell") == CELL and row.get("round") == 0 and not row.get("warmup"))
    response = check["response"]
    message = response["choices"][0]["message"]["content"]
    timings = response["timings"]
    hit_rows = re.findall(
        r"decode expert cache hit rate: ([0-9.]+)% \((\d+) hits / (\d+) lookups\)",
        (path / "engine.log").read_text(),
    )
    memory = [json.loads(line) for line in (path / "memory.jsonl").read_text().splitlines() if line]
    run = json.loads((path / "result.json").read_text())
    cpu_hz = [value["hz"] for sample in memory
              for value in sample.get("clock_observations", {}).get("cpu", {}).values()
              if value.get("hz")]
    gpu_hz = [sample["clock_observations"]["gpu"]["hz"] for sample in memory
              if sample.get("clock_observations", {}).get("gpu", {}).get("hz")]
    oom = max((int(counter.get("oom_kill", 0))
               for sample in memory for cgroup in sample.get("cgroups", [])
               for counter in [cgroup.get("memory_events", {})]), default=0)
    return {
        "status": check["status"],
        "prompt_tokens": response["usage"]["prompt_tokens"],
        "completion_tokens": response["usage"]["completion_tokens"],
        "prompt_tps": timings["prompt_per_second"],
        "decode_tps": timings["predicted_per_second"],
        "ttft_s": check["stream_observation"]["first_visible_delta_s"],
        "client_s": check["client_elapsed_s"],
        "answer_prefix_passed": message.startswith("NIMBUS-7319"),
        "response_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "decode_hit_history": [
            {"percent": float(pct), "hits": int(hits), "lookups": int(lookups)}
            for pct, hits, lookups in hit_rows
        ],
        "minimum_available_bytes": run["minimum_available_bytes"],
        "peak_swap_bytes": max((sample.get("swap_used_bytes", 0) for sample in memory), default=0),
        "oom_kill_max": oom,
        "cpu_clock_mhz_range": [min(cpu_hz) / 1e6, max(cpu_hz) / 1e6] if cpu_hz else None,
        "gpu_clock_mhz_range": [min(gpu_hz) / 1e6, max(gpu_hz) / 1e6] if gpu_hz else None,
        "emc_clock_observed": any(
            sample.get("clock_observations", {}).get("emc", {}).get("hz") for sample in memory
        ),
    }


def paired_advantage(candidate, baseline, metric):
    if metric in ("prompt_tps", "decode_tps"):
        return 100.0 * (candidate[metric] / baseline[metric] - 1.0)
    return 100.0 * (baseline[metric] / candidate[metric] - 1.0)


def bootstrap_median_interval(values, seed):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choice(values) for _ in values) for _ in range(100_000))
    return [samples[2499], samples[97499]]


def percentile_95(values):
    values = sorted(values)
    index = (len(values) - 1) * 0.95
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (index - low) * (values[high] - values[low])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("screen_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    pairs = []
    for pair in range(3):
        baseline = read_arm(args.screen_root, pair, "baseline")
        candidate = read_arm(args.screen_root, pair, "candidate")
        pairs.append({
            "pair": pair,
            "baseline": baseline,
            "candidate": candidate,
            "effects_percent": {
                name: paired_advantage(candidate, baseline, metric)
                for name, metric in (("prompt_tps", "prompt_tps"), ("decode_tps", "decode_tps"),
                                     ("ttft", "ttft_s"), ("client_time", "client_s"))
            },
        })
    metrics = {"prompt_tps": "prompt_tps", "decode_tps": "decode_tps",
               "ttft": "ttft", "client_time": "client_time"}
    paired = {}
    for name in metrics:
        values = [row["effects_percent"][name] for row in pairs]
        paired[name] = {
            "median_effect_percent": statistics.median(values),
            "bootstrap_95_interval_percent": bootstrap_median_interval(values, 20261031),
            "block_effects_percent": values,
        }
    arms = {}
    for arm in ("baseline", "candidate"):
        observations = [row[arm] for row in pairs]
        arms[arm] = {
            "median_prompt_tps": statistics.median(row["prompt_tps"] for row in observations),
            "median_decode_tps": statistics.median(row["decode_tps"] for row in observations),
            "median_ttft_s": statistics.median(row["ttft_s"] for row in observations),
            "median_client_s": statistics.median(row["client_s"] for row in observations),
            "descriptive_p95_client_s": percentile_95([row["client_s"] for row in observations]),
            "p95_sample_count": len(observations),
            "p95_method": "linear interpolation over the three independent request latencies; descriptive only",
        }
    result = {
        "schema": 1,
        "experiment": "Q2_0 NInfer vs Strata, adaptive 5000-slot cache, pp512+tg128 NIMBUS screen",
        "pair_count": len(pairs),
        "pairs": pairs,
        "arm_summary": arms,
        "paired_effects": paired,
        "resource_summary": {
            "minimum_available_bytes": min(row[arm]["minimum_available_bytes"]
                                             for row in pairs for arm in ("baseline", "candidate")),
            "maximum_swap_bytes": max(row[arm]["peak_swap_bytes"]
                                      for row in pairs for arm in ("baseline", "candidate")),
            "maximum_oom_kill_counter": max(row[arm]["oom_kill_max"]
                                           for row in pairs for arm in ("baseline", "candidate")),
            "cpu_clock_mhz_range": [
                min(row[arm]["cpu_clock_mhz_range"][0] for row in pairs for arm in ("baseline", "candidate")),
                max(row[arm]["cpu_clock_mhz_range"][1] for row in pairs for arm in ("baseline", "candidate")),
            ],
            "gpu_clock_mhz_range": [
                min(row[arm]["gpu_clock_mhz_range"][0] for row in pairs for arm in ("baseline", "candidate")),
                max(row[arm]["gpu_clock_mhz_range"][1] for row in pairs for arm in ("baseline", "candidate")),
            ],
            "emc_clock_observed": any(row[arm]["emc_clock_observed"]
                                       for row in pairs for arm in ("baseline", "candidate")),
            "energy_measured": False,
        },
        "quality_summary": {
            "all_checks_passed": all(row[arm]["status"] == "pass"
                                      for row in pairs for arm in ("baseline", "candidate")),
            "all_answer_prefixes_passed": all(row[arm]["answer_prefix_passed"]
                                               for row in pairs for arm in ("baseline", "candidate")),
            "single_response_hash": len({row[arm]["response_sha256"]
                                          for row in pairs for arm in ("baseline", "candidate")}) == 1,
            "all_requested_output_lengths_passed": all(row[arm]["prompt_tokens"] == 512
                                                       and row[arm]["completion_tokens"] == 128
                                                       for row in pairs for arm in ("baseline", "candidate")),
        },
        "scope": "three-pair screening only; adaptive residency policy is enabled in both arms; no quality claim beyond exact retrieval prefix, token count, and matching response text",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
