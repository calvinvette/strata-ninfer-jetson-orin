#!/usr/bin/env python3
"""Recompute paired request summaries and correctness checks for this run."""
import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign-retry"
CELLS = ("pp512+tg64", "pp2048+tg128")
METRICS = ("prompt_ms", "predicted_ms")


def load(block, arm):
    path = CAMPAIGN / f"block-{block}-{arm}" / "requests.json"
    data = json.loads(path.read_text())
    checks = {row["cell"]: row for row in data["checks"] if row["round"] == 0}
    assert set(checks) == set(CELLS)
    assert all(row["status"] == "pass" for row in checks.values())
    return checks


def percentile(values, q):
    values = sorted(values)
    return values[round((len(values) - 1) * q)]


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def bootstrap(deltas, seed):
    rng = random.Random(seed)
    samples = [median([rng.choice(deltas) for _ in deltas]) for _ in range(200000)]
    return [percentile(samples, 0.025), percentile(samples, 0.975)]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def request_value(row):
    return row["response"]["timings"]["prompt_ms"] + row["response"]["timings"]["predicted_ms"]


def delta(base, candidate):
    return 100 * (candidate / base - 1)


out = {"campaign": str(CAMPAIGN.relative_to(ROOT)), "blocks": [], "cells": {}}
minimum_available = 2**63
cache_capacities = []
clock_hz = {"cpu": [], "gpu": [], "emc": []}
for block in range(7):
    base, cand = load(block, "baseline"), load(block, "candidate")
    pair = {"block": block, "workload_order": [row["cell"] for row in base.values()], "cells": {}}
    for cell in CELLS:
        b, c = base[cell], cand[cell]
        br, cr = b["response"], c["response"]
        expected_prompt = int(cell.split("+")[0][2:])
        expected_completion = int(cell.split("+")[1][2:])
        assert br["usage"]["prompt_tokens"] == cr["usage"]["prompt_tokens"] == expected_prompt
        assert br["usage"]["completion_tokens"] == cr["usage"]["completion_tokens"] == expected_completion
        btext, ctext = br["choices"][0]["message"]["content"], cr["choices"][0]["message"]["content"]
        assert btext == ctext, f"output differs in block {block} {cell}"
        bt, ct = br["timings"], cr["timings"]
        assert bt["cache_n"] == ct["cache_n"] == 0
        item = {
            "baseline_request_wall_ms": b["client_elapsed_s"] * 1000,
            "candidate_request_wall_ms": c["client_elapsed_s"] * 1000,
            "baseline_prompt_ms": bt["prompt_ms"],
            "candidate_prompt_ms": ct["prompt_ms"],
            "baseline_decode_ms": bt["predicted_ms"],
            "candidate_decode_ms": ct["predicted_ms"],
            "baseline_output_sha256": digest(btext),
            "candidate_output_sha256": digest(ctext),
            "output_identical": True,
            "baseline_draft_n": bt.get("draft_n"),
            "candidate_draft_n": ct.get("draft_n"),
            "baseline_draft_n_accepted": bt.get("draft_n_accepted"),
            "candidate_draft_n_accepted": ct.get("draft_n_accepted"),
        }
        pair["cells"][cell] = item
    out["blocks"].append(pair)

for cell in CELLS:
    metric_rows = []
    for pair in out["blocks"]:
        row = pair["cells"][cell]
        row["request_ms"] = row["baseline_prompt_ms"] + row["baseline_decode_ms"]
        row["candidate_request_ms"] = row["candidate_prompt_ms"] + row["candidate_decode_ms"]
        metric_rows.append(row)
    metrics = {
        "request": ("request_ms", "candidate_request_ms"),
        "prompt": ("baseline_prompt_ms", "candidate_prompt_ms"),
        "decode": ("baseline_decode_ms", "candidate_decode_ms"),
        "client_request_wall": ("baseline_request_wall_ms", "candidate_request_wall_ms"),
    }
    summaries = {}
    for ix, (name, (bkey, ckey)) in enumerate(metrics.items()):
        deltas = [delta(row[bkey], row[ckey]) for row in metric_rows]
        summaries[name] = {
            "baseline_median": median([row[bkey] for row in metric_rows]),
            "candidate_median": median([row[ckey] for row in metric_rows]),
            "paired_candidate_delta_percent": deltas,
            "median_paired_candidate_delta_percent": median(deltas),
            "paired_bootstrap_95_percentile_interval": bootstrap(deltas, 202610128 + ix),
            "bootstrap_replicates": 200000,
        }
    out["cells"][cell] = {"samples": metric_rows, "summary": summaries}

for block in range(7):
    for arm in ("baseline", "candidate"):
        result = json.loads((CAMPAIGN / f"block-{block}-{arm}" / "result.json").read_text())
        assert result["status"] == "pass"
        minimum_available = min(minimum_available, result["minimum_available_bytes"])
        assert result["minimum_available_bytes"] >= 6 * 1024**3
        engine_log = (CAMPAIGN / f"block-{block}-{arm}" / "engine.log").read_text(errors="replace")
        match = re.search(r"expert cache (\d+) slots", engine_log)
        assert match, f"missing actual cache capacity in block {block} {arm}"
        cache_capacities.append(int(match.group(1)))
        for line in (CAMPAIGN / f"block-{block}-{arm}" / "memory.jsonl").open():
            observation = json.loads(line).get("clock_observations", {})
            for key in clock_hz:
                values = ([row.get("hz") for row in observation.get("cpu", {}).values()]
                          if key == "cpu" else [observation.get(key, {}).get("hz")])
                clock_hz[key].extend(value for value in values if value is not None)
out["memory"] = {"six_gib_floor_bytes": 6 * 1024**3,
                 "minimum_available_bytes": minimum_available,
                 "minimum_available_gib": minimum_available / 1024**3,
                 "all_supervisors_passed": True}
assert len(set(cache_capacities)) == 1, cache_capacities
out["actual_expert_cache_slots"] = {"per_process": cache_capacities, "matched": True}
out["observed_dynamic_clock_hz"] = {
    key: {"minimum": min(values), "maximum": max(values), "samples": len(values)}
    for key, values in clock_hz.items() if values
}
out["qualification"] = (
    "Seven randomized same-day process pairs; exact API workload/output checks passed. "
    "Request time is prompt_ms + predicted_ms. Timing evidence is specific to these two prompts, "
    "model, context and runtime settings; dynamic clocks and no energy measurement limit interpretation."
)
(ROOT / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
for cell, report in out["cells"].items():
    print(cell)
    for name, summary in report["summary"].items():
        print(name, f"median paired delta {summary['median_paired_candidate_delta_percent']:.3f}%",
              f"95% [{summary['paired_bootstrap_95_percentile_interval'][0]:.3f}%, "
              f"{summary['paired_bootstrap_95_percentile_interval'][1]:.3f}%]")
print("minimum_available_gib", f"{out['memory']['minimum_available_gib']:.3f}")
