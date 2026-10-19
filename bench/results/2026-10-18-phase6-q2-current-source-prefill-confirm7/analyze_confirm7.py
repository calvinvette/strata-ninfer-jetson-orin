#!/usr/bin/env python3
"""Validate and summarize seven current-source Q2_0 chunk-size pairs."""
import argparse
import csv
import gzip
import json
import random
import statistics
import sys
from pathlib import Path

ROOT_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_REPO / "tools" / "integration"))
from request_telemetry import rails_from_lines, window_energy

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
root = ap.parse_args().root.resolve()
blocks = [f"block-{i:02d}" for i in range(1, 8)]
workload = json.loads((root / "workload.json").read_text())["workloads"][0]
codes = workload["expected_codes"]
expected = (f"EARLY={codes[0]}, MIDDLE={codes[1]}, LATE={codes[2]}, "
            f"SUM={workload['expected_suffix_sum']}")
gib = 1024 ** 3
rows = []
paired = {"request_ms": [], "prompt_ms": [], "decode_ms": [],
          "vin_sys_j_per_token": [], "vdd_gpu_j_per_token": []}
minimum_host = minimum_admission = None
samples_count = 0
max_events = {name: 0 for name in ("low", "high", "max", "oom", "oom_kill")}
gpu_hz, cpu_hz, temperatures = [], [], []
energy_status = {}


def read_lines(path):
    compressed = path.with_suffix(path.suffix + ".gz")
    if compressed.exists():
        with gzip.open(compressed, "rt") as source:
            return source.read().splitlines()
    return path.read_text().splitlines()


for block in blocks:
    campaign = json.loads((root / block / "campaign.json").read_text())
    assert campaign["clock_sampling"] and campaign["independent_block_confirmation"]
    assert campaign["rounds_per_service"] == 1 and len(campaign["cells"]) == 2
    assert {cell["prefill_chunk_tokens"] for cell in campaign["cells"]} == {32, 128}
    assert all(cell["expert_cache_argument"] == 3000 and cell["status"] == "pass"
               for cell in campaign["cells"])
    block_rows = {}
    for cell in campaign["cells"]:
        folder = root / block / cell["name"]
        request_log = json.loads((folder / "requests.json").read_text())
        measured = [item for item in request_log["checks"] if not item.get("warmup")]
        assert len(measured) == 1 and measured[0]["status"] == "pass"
        req = measured[0]
        response = req["response"]
        answer = response["choices"][0]["message"]["content"]
        usage, timing = response["usage"], response["timings"]
        assert answer == expected, (block, cell["name"], answer)
        completion = usage["completion_tokens"]
        assert usage["prompt_tokens"] == workload["prompt_tokens"] == 512
        assert completion == 47 and timing.get("cache_n", 0) == 0
        assert timing["prompt_n"] == 512 and timing["predicted_n"] == completion
        config = json.loads((folder / "config.json").read_text())
        args = config["args"]
        assert int(args[args.index("--expert-cache") + 1]) == 3000
        chunk = int(args[args.index("--prefill") + 1])
        assert chunk == cell["prefill_chunk_tokens"]
        capability = json.loads((folder / "capabilities.json").read_text())["engine"]
        assert capability["expert_slots"] == 3000 and capability["context"] == 8192
        assert capability["kv"] == "fp16" and capability["mtp_max"] == 0
        assert capability["spec"] == 2 and capability["pool_workers"] == 8
        assert capability["conversation_cache_mib"] == 0

        supervisor = json.loads((folder / "supervisor/result.json").read_text())
        assert supervisor["status"] == "pass" and supervisor["floor_bytes"] == 6 * gib
        memory_rows = [json.loads(line) for line in read_lines(folder / "supervisor/memory.jsonl")]
        assert memory_rows and supervisor["minimum_admission_available_bytes"] >= 6 * gib
        offset = memory_rows[0]["wall_time_s"] - memory_rows[0]["monotonic_s"]
        rails = rails_from_lines(read_lines(folder / "supervisor/tegrastats.txt"))
        energy = window_energy(rails,
            req["request_start_monotonic_s"] + offset,
            req["request_end_monotonic_s"] + offset)
        energy_status[block + "/" + cell["name"]] = energy["status"]
        rail_energy = energy.get("joules_by_named_rail", {})
        active = [sample for sample in memory_rows
                  if req["request_start_monotonic_s"] <= sample["monotonic_s"] <=
                  req["request_end_monotonic_s"]]
        assert active, (block, cell["name"], "missing in-request telemetry")
        request_cpu = [item["hz"] for sample in active
                       for item in sample["clock_observations"]["cpu"].values()
                       if item.get("hz")]
        for sample in memory_rows:
            samples_count += 1
            minimum_host = min(minimum_host or sample["available_bytes"], sample["available_bytes"])
            minimum_admission = min(minimum_admission or sample["admission_available_bytes"],
                                    sample["admission_available_bytes"])
            gpu_hz.append(sample["clock_observations"]["gpu"]["hz"])
            cpu_hz.extend(item["hz"] for item in sample["clock_observations"]["cpu"].values()
                          if item.get("hz"))
            for cgroup in sample["cgroups"]:
                if cgroup["max_bytes"] is not None:
                    assert cgroup["max_bytes"] == 28 * gib
                for name in max_events:
                    value = cgroup.get("memory_events", {}).get(name, 0)
                    max_events[name] = max(max_events[name], value)
                    assert value == 0, (block, cell["name"], name, value)
        row = {"block": block, "cell": cell["name"], "prefill_chunk": chunk,
               "request_ms": timing["prompt_ms"] + timing["predicted_ms"],
               "prompt_ms": timing["prompt_ms"], "decode_ms": timing["predicted_ms"],
               "prompt_tok_s": timing["prompt_per_second"],
               "decode_tok_s": timing["predicted_per_second"],
               "completion_tokens": completion,
               "minimum_host_gib": supervisor["minimum_available_bytes"] / gib,
               "minimum_admission_gib": supervisor["minimum_admission_available_bytes"] / gib,
               "request_gpu_hz_median": statistics.median(
                   sample["clock_observations"]["gpu"]["hz"] for sample in active),
               "request_cpu_hz_median": statistics.median(request_cpu),
               "request_clock_samples": len(active),
               "rail_energy_status": energy["status"],
               "joules_per_output_token_by_named_rail":
                   {name: value / completion for name, value in rail_energy.items()}}
        rows.append(row)
        block_rows[chunk] = row
    for metric in paired:
        base = block_rows[32]
        candidate = block_rows[128]
        if metric == "vin_sys_j_per_token":
            a = base["joules_per_output_token_by_named_rail"].get("VIN_SYS_5V0")
            b = candidate["joules_per_output_token_by_named_rail"].get("VIN_SYS_5V0")
        elif metric == "vdd_gpu_j_per_token":
            a = base["joules_per_output_token_by_named_rail"].get("VDD_GPU_SOC")
            b = candidate["joules_per_output_token_by_named_rail"].get("VDD_GPU_SOC")
        else:
            a = base[metric]
            b = candidate[metric]
        if a is not None and b is not None:
            paired[metric].append(100 * (b / a - 1))


def bootstrap(values, seed):
    rng = random.Random(seed)
    draws = sorted(statistics.median(rng.choices(values, k=len(values)))
                   for _ in range(100000))
    return [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))]]


contrasts = {}
for index, (metric, values) in enumerate(paired.items()):
    contrasts[metric] = {
        "paired_blocks": len(values),
        "chunk128_vs_chunk32_median_percent_change": statistics.median(values) if values else None,
        "paired_block_bootstrap_95pct_percent": bootstrap(values, 2026101800 + index)
            if values else None,
        "block_effects_percent": values,
    }
minimum_host = min(minimum_host, *(row["minimum_host_gib"] * gib for row in rows))
minimum_admission = min(minimum_admission, *(row["minimum_admission_gib"] * gib for row in rows))
summary = {
    "scope": "Seven randomized independent same-day blocks; one measured 512-token held-out retrieval-and-sum request per fresh process/cell after a separate warmup; Q2_0, FP16 KV, MTP off, 3,000 exact cache slots, 8K context, 8 workers; current-source candidate.",
    "source_commit": "0b28cd634fa3a7ba9da514df0200d96baea330e4",
    "candidate_binary_sha256": "320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932",
    "expected_answer": expected,
    "blocks": blocks,
    "cells": rows,
    "paired_contrasts": contrasts,
    "validation": {
        "blocks": 7, "measured_requests": len(rows), "all_answers_exact": len(rows) == 14,
        "all_supervisors_pass": len(rows) == 14,
        "minimum_host_available_gib": minimum_host / gib,
        "minimum_admission_available_gib": minimum_admission / gib,
        "six_gib_floor_bytes": 6 * gib, "memory_samples": samples_count,
        "maximum_cgroup_events": max_events,
        "all_rail_windows_estimated": all(v == "estimated" for v in energy_status.values()),
        "rail_window_status": energy_status,
        "gpu_clock_hz_range": [min(gpu_hz), max(gpu_hz)],
        "cpu_clock_hz_range": [min(cpu_hz), max(cpu_hz)],
        "energy_scope": "named tegrastats rails integrated per request; includes board idle/background, not process-attributed; rails are kept separate and not summed",
        "clock_policy": "dynamic clocks; observed read-only; no clock changes",
    },
}
(root / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
with (root / "measurements.csv").open("w", newline="") as output:
    fields = list(rows[0])
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
by_block = {block: {row["prefill_chunk"]: row for row in rows if row["block"] == block}
            for block in blocks}
pair_rows = []
for block in blocks:
    base, candidate = by_block[block][32], by_block[block][128]
    pair = {"block": block}
    for metric in ("request_ms", "prompt_ms", "decode_ms"):
        pair[f"chunk32_{metric}"] = base[metric]
        pair[f"chunk128_{metric}"] = candidate[metric]
        pair[f"chunk128_vs_32_{metric}_percent"] = 100 * (candidate[metric] / base[metric] - 1)
    for rail in ("VIN_SYS_5V0", "VDD_GPU_SOC"):
        a = base["joules_per_output_token_by_named_rail"].get(rail)
        b = candidate["joules_per_output_token_by_named_rail"].get(rail)
        pair[f"chunk32_{rail}_j_per_output_token"] = a
        pair[f"chunk128_{rail}_j_per_output_token"] = b
        pair[f"chunk128_vs_32_{rail}_percent"] = 100 * (b / a - 1) if a and b else None
    pair_rows.append(pair)
with (root / "paired-blocks.csv").open("w", newline="") as output:
    fields = list(pair_rows[0])
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(pair_rows)
print(json.dumps({"validation": summary["validation"], "paired_contrasts": contrasts}, indent=2))
