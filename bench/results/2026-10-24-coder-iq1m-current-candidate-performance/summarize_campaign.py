#!/usr/bin/env python3
"""Summarize the raw Coder IQ1_M campaign without joining other cohorts."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import statistics


ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign"


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p + 0.999999)))]


def metric_summary(values, seed):
    values = [float(x) for x in values]
    rng = random.Random(seed)
    boot = [statistics.median(rng.choices(values, k=len(values))) for _ in range(20000)]
    return {
        "n": len(values), "median": statistics.median(values),
        "min": min(values), "max": max(values),
        "bootstrap_95_percentile_interval_for_median": [percentile(boot, .025), percentile(boot, .975)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=CAMPAIGN)
    parser.add_argument("--output", type=Path, default=ROOT / "summary.json")
    args = parser.parse_args()
    campaign_root = args.campaign
    campaign = json.loads((campaign_root / "campaign.json").read_text())
    runs = campaign["runs"]
    if len(runs) != 7 or any(row["status"] != "pass" for row in runs):
        raise SystemExit("expected seven passing independent process blocks")
    all_rows = {}
    request_telemetry = {}
    for run in runs:
        block = campaign_root / f"block-{run['block']:02d}"
        path = block / "requests.json"
        payload = json.loads(path.read_text())
        for row in payload["checks"]:
            if row["warmup"]:
                continue
            all_rows.setdefault(row["cell"], []).append(row)
            samples = [json.loads(line) for line in
                       (block / "supervisor/memory.jsonl").read_text().splitlines() if line.strip()]
            start, end = row["request_start_monotonic_s"], row["request_end_monotonic_s"]
            start_sample = min(samples, key=lambda x: abs(x["monotonic_s"] - start))
            end_sample = min(samples, key=lambda x: abs(x["monotonic_s"] - end))
            within = [s for s in samples if start <= s["monotonic_s"] <= end] or [start_sample, end_sample]

            def nvme(snapshot):
                for line in snapshot["host_diskstats"].splitlines():
                    fields = line.split()
                    if len(fields) >= 10 and fields[2] == "nvme0n1":
                        return int(fields[5]) * 512, int(fields[9]) * 512
                raise ValueError("nvme0n1 missing from retained host diskstats")

            read0, write0 = nvme(start_sample)
            read1, write1 = nvme(end_sample)
            request_telemetry.setdefault(row["cell"], []).append({
                "nvme_read_bytes": read1 - read0, "nvme_write_bytes": write1 - write0,
                "min_memavailable_bytes": min(s["available_bytes"] for s in within),
                "min_admission_available_bytes": min(s["admission_available_bytes"] for s in within),
                "max_swap_used_bytes": max(s["swap_used_bytes"] for s in within),
                "max_endpoint_gap_s": max(abs(start_sample["monotonic_s"] - start),
                                           abs(end_sample["monotonic_s"] - end)),
            })
    summary = {
        "campaign_seed": campaign["seed"], "independent_process_blocks": len(runs),
        "status": "pass", "cells": {}, "memory": {}, "clocks": {},
        "qualification": "performance only; exact token counts and fresh prefill passed; no output-quality oracle",
        "uncertainty": "20,000 nonparametric bootstrap resamples of independent process blocks; percentile interval for the median",
    }
    for index, (cell, rows) in enumerate(sorted(all_rows.items())):
        if len(rows) != 7 or any(row["status"] != "pass" for row in rows):
            raise SystemExit(f"{cell}: expected seven passing measured requests")
        fields = {
            "prompt_tokens_per_second": [r["response"]["timings"]["prompt_per_second"] for r in rows],
            "generated_tokens_per_second_engine_reported": [r["response"]["timings"]["predicted_per_second"] for r in rows],
            "engine_prompt_ms": [r["response"]["timings"]["prompt_ms"] for r in rows],
            "engine_generated_ms": [r["response"]["timings"]["predicted_ms"] for r in rows],
            "client_ttft_s": [r["stream_observation"]["first_visible_delta_s"] for r in rows],
            "client_total_request_s": [r["client_elapsed_s"] for r in rows],
            "completion_tokens": [r["response"]["usage"]["completion_tokens"] for r in rows],
        }
        content_hashes = [hashlib.sha256(r["response"]["choices"][0]["message"]["content"].encode()).hexdigest()
                          for r in rows]
        summary["cells"][cell] = {
            "measured_requests": len(rows),
            "prompt_tokens": sorted({r["response"]["usage"]["prompt_tokens"] for r in rows}),
            "completion_tokens_observed": sorted({r["response"]["usage"]["completion_tokens"] for r in rows}),
            "unique_output_text_hashes": len(set(content_hashes)),
            "output_text_sha256_by_block": content_hashes,
            "metrics": {name: metric_summary(values, 2026102401 + index * 100 + j)
                        for j, (name, values) in enumerate(fields.items())},
            "request_aligned_physical_observations": {
                "minimum_sampled_MemAvailable_GiB": min(x["min_memavailable_bytes"] for x in request_telemetry[cell]) / 2**30,
                "minimum_sampled_admission_available_GiB": min(x["min_admission_available_bytes"] for x in request_telemetry[cell]) / 2**30,
                "median_host_nvme_read_GB_per_request": statistics.median(x["nvme_read_bytes"] for x in request_telemetry[cell]) / 1e9,
                "median_host_nvme_write_GB_per_request": statistics.median(x["nvme_write_bytes"] for x in request_telemetry[cell]) / 1e9,
                "maximum_disk_endpoint_gap_s": max(x["max_endpoint_gap_s"] for x in request_telemetry[cell]),
                "scope": "host-wide /proc/diskstats nvme0n1 deltas, not process-attributed; concurrent I/O and read-ahead included",
            },
            "p95_request_latency": "maximum of seven observations (descriptive only)",
        }
    minimum_available, minimum_admission, maximum_swap = [], [], []
    cpu_hz, gpu_hz, tj_c, emc_statuses, cgroup_events = [], [], [], [], {}
    for run in runs:
        block = campaign_root / f"block-{run['block']:02d}"
        result = json.loads((block / "supervisor/result.json").read_text())
        minimum_available.append(result["minimum_available_bytes"])
        minimum_admission.append(result["minimum_admission_available_bytes"])
        for line in (block / "supervisor/memory.jsonl").read_text().splitlines():
            sample = json.loads(line)
            maximum_swap.append(sample["swap_used_bytes"])
            clock = sample.get("clock_observations", {})
            cpu_hz.extend(v["hz"] for v in clock.get("cpu", {}).values() if isinstance(v.get("hz"), int))
            if isinstance(clock.get("gpu", {}).get("hz"), int):
                gpu_hz.append(clock["gpu"]["hz"])
            emc_statuses.append(clock.get("emc", {}).get("status", "not_sampled"))
            for cg in sample.get("cgroups", []):
                for key, value in cg.get("memory_events", {}).items():
                    cgroup_events[key] = max(cgroup_events.get(key, 0), value)
        for line in (block / "supervisor/tegrastats.txt").read_text().splitlines():
            match = re.search(r"\btj@([\d.]+)C", line)
            if match:
                tj_c.append(float(match.group(1)))
    summary["memory"] = {
        "minimum_MemAvailable_GiB": min(minimum_available) / 2**30,
        "minimum_admission_available_GiB": min(minimum_admission) / 2**30,
        "maximum_swap_used_GiB": max(maximum_swap) / 2**30,
        "cgroup_memory_event_maxima": cgroup_events,
        "note": "process RSS is CPU-only and is not a GPU-inclusive physical memory total",
    }
    summary["clocks"] = {
        "cpu_observed_GHz_min_max": [min(cpu_hz) / 1e9, max(cpu_hz) / 1e9] if cpu_hz else None,
        "gpu_observed_MHz_min_max": [min(gpu_hz) / 1e6, max(gpu_hz) / 1e6] if gpu_hz else None,
        "tj_C_min_max": [min(tj_c), max(tj_c)] if tj_c else None,
        "tegrastats_temperature_samples": len(tj_c),
        "emc_readback_statuses": sorted(set(emc_statuses)),
        "policy": "MAXN; dynamic clocks observed, not controlled",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
