#!/usr/bin/env python3
"""Estimate named board-rail energy in each paired API request window."""
import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools/integration"))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

arms = []
for block in range(1, 8):
    for cache in (1500, 3000):
        run = HERE / f"per-cell-scopes/block-{block:02d}/cache{cache}-ctx16384"
        requests = json.loads((run / "requests.json").read_text())
        measured = [x for x in requests["checks"] if not x.get("warmup")]
        if len(measured) != 3 or any(x.get("status") != "pass" for x in measured):
            raise RuntimeError(f"invalid measured requests in block {block}, cache {cache}")
        memory = [json.loads(line) for line in (run / "supervisor/memory.jsonl").read_text().splitlines()]
        if not memory:
            raise RuntimeError(f"missing memory clock for block {block}, cache {cache}")
        offset = memory[0]["wall_time_s"] - memory[0]["monotonic_s"]
        samples = rails_from_lines((run / "supervisor/tegrastats.txt").read_text().splitlines())
        for request in measured:
            start = request["request_start_monotonic_s"] + offset
            end = request["request_end_monotonic_s"] + offset
            energy = window_energy(samples, start, end)
            tokens = request["response"]["usage"]["completion_tokens"]
            rails = energy.get("joules_by_named_rail", {})
            arms.append({
                "block": block,
                "cache_mib": cache,
                "round": request["round"],
                "status": energy["status"],
                "reason": energy.get("reason"),
                "request_seconds": request["request_end_monotonic_s"] - request["request_start_monotonic_s"],
                "output_tokens": tokens,
                "joules_by_named_rail": rails,
                "joules_per_output_token_by_named_rail": {k: v / tokens for k, v in rails.items()},
            })

paired = []
for block in range(1, 8):
    a = [x for x in arms if x["block"] == block and x["cache_mib"] == 1500]
    b = [x for x in arms if x["block"] == block and x["cache_mib"] == 3000]
    if len(a) != 3 or len(b) != 3 or any(x["status"] != "estimated" for x in a + b):
        continue
    for rail in sorted(set.intersection(*(set(x["joules_by_named_rail"]) for x in a + b))):
        energy_a = statistics.median(x["joules_by_named_rail"][rail] for x in a)
        energy_b = statistics.median(x["joules_by_named_rail"][rail] for x in b)
        per_token_a = statistics.median(x["joules_per_output_token_by_named_rail"][rail] for x in a)
        per_token_b = statistics.median(x["joules_per_output_token_by_named_rail"][rail] for x in b)
        paired.append({
            "block": block,
            "rail": rail,
            "cache1500_median_j": energy_a,
            "cache3000_median_j": energy_b,
            "cache1500_median_j_per_token": per_token_a,
            "cache3000_median_j_per_token": per_token_b,
            "cache3000_over_1500_ratio": energy_b / energy_a,
        })

summary = []
for rail in sorted({x["rail"] for x in paired}):
    rows = [x for x in paired if x["rail"] == rail]
    ratios = [x["cache3000_over_1500_ratio"] for x in rows]
    low, high = interval(ratios, 2026102127)
    summary.append({
        "rail": rail,
        "paired_blocks": len(rows),
        "cache1500_median_j": statistics.median(x["cache1500_median_j"] for x in rows),
        "cache3000_median_j": statistics.median(x["cache3000_median_j"] for x in rows),
        "cache1500_median_j_per_token": statistics.median(x["cache1500_median_j_per_token"] for x in rows),
        "cache3000_median_j_per_token": statistics.median(x["cache3000_median_j_per_token"] for x in rows),
        "cache3000_over_1500_median_percent_change": (statistics.median(ratios) - 1) * 100,
        "paired_bootstrap_95_interval_percent": [(low - 1) * 100, (high - 1) * 100],
    })

out = {
    "scope": "Separate named tegrastats rails integrated over each API request window. Includes board idle/background activity; not process-attributed and rails are not summed.",
    "method": "Piecewise-linear integration of instantaneous mW; request timestamps mapped using supervisor wall/monotonic offset; one-second readings with gaps over 2.5 seconds rejected.",
    "attempts": len(arms),
    "estimated_windows": sum(x["status"] == "estimated" for x in arms),
    "unsupported_windows": sum(x["status"] != "estimated" for x in arms),
    "paired_block_count": len({x["block"] for x in paired}),
    "per_request": arms,
    "paired": paired,
    "summary": summary,
}
(HERE / "rail-energy.json").write_text(json.dumps(out, indent=2) + "\n")
with (HERE / "rail-energy-pairs.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(paired[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(paired)
print(json.dumps({"estimated": out["estimated_windows"], "unsupported": out["unsupported_windows"], "summary": summary}, indent=2))
