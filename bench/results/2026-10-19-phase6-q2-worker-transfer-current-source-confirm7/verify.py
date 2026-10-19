#!/usr/bin/env python3
"""Independently verify current-source worker-transfer answers and supervision."""
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign"
EXPECTED = ("EARLY=JADE-COMET-482, MIDDLE=CRIMSON-DELTA-137, "
            "LATE=PEARL-FOREST-809, SUM=1428")
CONDITIONS = {(workers, mode) for workers in (4, 8) for mode in ("mapped", "pread")}


def require(ok, message):
    if not ok:
        raise SystemExit(message)


data = json.loads((CAMPAIGN / "results.json").read_text())
require(data.get("passed") is True and not data.get("failures"), "campaign runner did not pass")
require(data.get("planned_repetitions") == 7 and data.get("engine_sha256") ==
        "b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa", "campaign identity mismatch")
require(data.get("actual_cache_slots_equal") and data.get("measured_output_equal"),
        "campaign cache or output hashes differ")
require(len(data["runs"]) == 28, "expected 28 measured cells")

seen = set()
measured_rows = []
answer_hashes = set()
for run in data["runs"]:
    cell = run["repetition"], run["workers"], run["transfer_mode"]
    require(cell not in seen, f"duplicate cell: {cell}")
    seen.add(cell)
    require((run["workers"], run["transfer_mode"]) in CONDITIONS, f"unexpected condition: {cell}")
    require(run.get("actual_expert_cache_slots") == 3000, f"cache capacity differs: {cell}")
    require("failure" not in run, f"campaign cell failed: {cell}")
    req_path = CAMPAIGN / "runs" / f"rep-{run['repetition']:02d}-workers-{run['workers']}-{run['transfer_mode']}" / "requests.json"
    req = json.loads(req_path.read_text())
    checks = [row for row in req["checks"] if not row.get("warmup")]
    require(len(checks) == 1 and checks[0].get("status") == "pass", f"measured API request missing: {cell}")
    row = checks[0]
    response = row["response"]
    content = response["choices"][0]["message"]["content"].strip()
    usage = response["usage"]
    metrics = response["timings"]
    require(content == EXPECTED, f"incorrect answer: {cell}: {content!r}")
    require(usage["prompt_tokens"] == 512 and usage["completion_tokens"] == 46,
            f"token counts differ: {cell}: {usage}")
    require(usage["prompt_tokens_details"]["cached_tokens"] == 0, f"prompt was cached: {cell}")
    require(metrics["cache_n"] == 0 and metrics["prompt_n"] == 512 and metrics["predicted_n"] == 46,
            f"engine token counts differ: {cell}")
    answer_hashes.add(hashlib.sha256(content.encode()).hexdigest())
    measured_rows.append({"block": run["repetition"], "workers": run["workers"],
                          "transfer": run["transfer_mode"], "request_ms": run["request_ms"],
                          "prompt_ms": run["prompt_ms"], "decode_ms": run["decode_ms"],
                          "ttft_ms": run["ttft_ms"], "output_sha256": run["output_sha256"]})
require(len(seen) == 28 and len({row["block"] for row in measured_rows}) == 7,
        "incomplete block × condition matrix")
require(len(answer_hashes) == 1, "answers differ across cells")

supervisor = ROOT / "supervisor"
summary = json.loads((supervisor / "result.json").read_text())
samples = [json.loads(line) for line in (supervisor / "memory.jsonl").read_text().splitlines()]
scope = [cg for sample in samples for cg in sample["cgroups"] if cg["path"].endswith(".scope")]
require(summary.get("status") == "pass" and len(samples) == 2237, "supervisor evidence is incomplete")
events = {key: max(cg["memory_events"].get(key, 0) for cg in scope)
          for key in ("low", "high", "max", "oom", "oom_kill")}
require(not any(events.values()), f"cgroup memory events observed: {events}")
require(summary["minimum_available_bytes"] >= 6 * 1024**3, "six-GiB host floor breached")
require(summary["minimum_admission_available_bytes"] >= 6 * 1024**3,
        "six-GiB admission floor breached")

effects = data["factorial_effects"]
intervals = effects["bootstrap_95pct_median_intervals"]
condition_summary = data["summary"]
with (ROOT / "condition-medians.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(("workers", "transfer", "n", "median_prompt_ms", "median_decode_ms",
                     "median_ttft_ms", "median_request_ms"))
    for workers in (4, 8):
        for mode in ("mapped", "pread"):
            row = condition_summary[str(workers)][mode]
            writer.writerow((workers, mode, row["samples"], row["median_prompt_ms"],
                             row["median_decode_ms"], row["median_ttft_ms"], row["median_request_ms"]))

paired = [
    ("4 vs 8 workers", "mapped", effects["worker_delta_percent_by_mode"]["mapped"]["4"],
     intervals["worker_delta_percent_by_mode"]["mapped"]["4"]),
    ("4 vs 8 workers", "pread", effects["worker_delta_percent_by_mode"]["pread"]["4"],
     intervals["worker_delta_percent_by_mode"]["pread"]["4"]),
    ("pread vs mapped", "4 workers", effects["pread_delta_percent_by_workers"]["4"],
     intervals["pread_delta_percent_by_workers"]["4"]),
    ("pread vs mapped", "8 workers", effects["pread_delta_percent_by_workers"]["8"],
     intervals["pread_delta_percent_by_workers"]["8"]),
    ("worker × transfer interaction", "difference-in-differences",
     effects["interaction_percentage_points"], intervals["interaction_percentage_points"]),
]
with (ROOT / "paired-effects.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(("contrast", "cell", "paired_median_effect", "ci95_low", "ci95_high", "units"))
    for contrast, cell, values, interval in paired:
        writer.writerow((contrast, cell, statistics.median(values), interval[0], interval[1],
                         "percentage_points" if "interaction" in contrast else "percent"))

gpu = [sample.get("clock_observations", {}).get("gpu", {}).get("hz") for sample in samples]
gpu = [value for value in gpu if isinstance(value, int)]
cpu = [core.get("hz") for sample in samples
       for core in sample.get("clock_observations", {}).get("cpu", {}).values()]
cpu = [value for value in cpu if isinstance(value, int)]
temp_values = []
for line in (supervisor / "tegrastats.txt").read_text(errors="replace").splitlines():
    match = re.search(r"tj@([0-9.]+)C", line)
    if match:
        temp_values.append(float(match.group(1)))

verification = {
    "passed": True,
    "matrix_cells": len(seen),
    "blocks": 7,
    "conditions": ["4/mapped", "8/mapped", "4/pread", "8/pread"],
    "all_exact_answers_equal": True,
    "exact_answer": EXPECTED,
    "prompt_tokens": 512,
    "completion_tokens": 46,
    "actual_expert_slots": 3000,
    "supervisor_samples": len(samples),
    "minimum_available_bytes": summary["minimum_available_bytes"],
    "minimum_admission_available_bytes": summary["minimum_admission_available_bytes"],
    "cgroup_event_maxima": events,
    "observed_gpu_hz_range": [min(gpu), max(gpu)] if gpu else None,
    "observed_cpu_hz_range": [min(cpu), max(cpu)] if cpu else None,
    "tegrastats_tj_c_range": [min(temp_values), max(temp_values)] if temp_values else None,
    "instrumentation": "timing-only; accepted-prefix tracing disabled",
}
(ROOT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print(json.dumps(verification, indent=2))
