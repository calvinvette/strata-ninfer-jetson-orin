#!/usr/bin/env python3
"""Integrate named board rails for current-source worker-transfer requests."""
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "tools/integration"))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

campaign = json.loads((ROOT / "campaign/results.json").read_text())
memory = [json.loads(line) for line in (ROOT / "supervisor/memory.jsonl").read_text().splitlines()]
offset = memory[0]["wall_time_s"] - memory[0]["monotonic_s"]
rails = rails_from_lines((ROOT / "supervisor/tegrastats.txt").read_text(errors="replace").splitlines())
per_arm = {}
for run in campaign["runs"]:
    key = (run["repetition"], run["workers"], run["transfer_mode"])
    run_dir = ROOT / "campaign/runs" / f"rep-{key[0]:02d}-workers-{key[1]}-{key[2]}"
    request = json.loads((run_dir / "requests.json").read_text())
    row = next(item for item in request["checks"] if not item.get("warmup"))
    energy = window_energy(rails, row["request_start_monotonic_s"] + offset,
                           row["request_end_monotonic_s"] + offset)
    tokens = row["response"]["usage"]["completion_tokens"]
    per_arm[key] = {
        "block": key[0], "workers": key[1], "transfer": key[2],
        "output_tokens": tokens, "request_seconds": row["request_end_monotonic_s"] - row["request_start_monotonic_s"],
        "status": energy["status"], "reason": energy.get("reason"),
        "joules_by_named_rail": energy.get("joules_by_named_rail", {}),
        "joules_per_output_token_by_named_rail": {
            name: value / tokens for name, value in energy.get("joules_by_named_rail", {}).items()},
    }

conditions = ((4, "mapped"), (8, "mapped"), (4, "pread"), (8, "pread"))
blocks = sorted({key[0] for key in per_arm})
contrasts = []
rails_present = sorted({name for row in per_arm.values() for name in row["joules_by_named_rail"]})
for rail in rails_present:
    definitions = (
        ("4 vs 8 workers", "mapped", lambda b: (b, 4, "mapped"), lambda b: (b, 8, "mapped"), "percent"),
        ("4 vs 8 workers", "pread", lambda b: (b, 4, "pread"), lambda b: (b, 8, "pread"), "percent"),
        ("pread vs mapped", "4 workers", lambda b: (b, 4, "pread"), lambda b: (b, 4, "mapped"), "percent"),
        ("pread vs mapped", "8 workers", lambda b: (b, 8, "pread"), lambda b: (b, 8, "mapped"), "percent"),
    )
    for contrast, cell, left_key, right_key, units in definitions:
        effects = []
        for block in blocks:
            left, right = per_arm[left_key(block)], per_arm[right_key(block)]
            if left["status"] == right["status"] == "estimated" and rail in left["joules_by_named_rail"] and rail in right["joules_by_named_rail"]:
                effects.append(100 * (left["joules_by_named_rail"][rail] / right["joules_by_named_rail"][rail] - 1))
        contrasts.append({"rail": rail, "contrast": contrast, "cell": cell,
                          "paired_blocks": len(effects), "block_effects": effects,
                          "median_effect": statistics.median(effects) if effects else None,
                          "bootstrap_95_interval": interval(effects, 2026101921) if len(effects) >= 2 else None,
                          "units": units})
    interaction = []
    for block in blocks:
        a, b, c, d = (per_arm[(block, 4, "pread")], per_arm[(block, 4, "mapped")],
                      per_arm[(block, 8, "pread")], per_arm[(block, 8, "mapped")])
        if all(x["status"] == "estimated" and rail in x["joules_by_named_rail"] for x in (a, b, c, d)):
            interaction.append(100 * (a["joules_by_named_rail"][rail] / b["joules_by_named_rail"][rail] - 1)
                               - 100 * (c["joules_by_named_rail"][rail] / d["joules_by_named_rail"][rail] - 1))
    contrasts.append({"rail": rail, "contrast": "worker × transfer interaction",
                      "cell": "difference-in-differences", "paired_blocks": len(interaction),
                      "block_effects": interaction,
                      "median_effect": statistics.median(interaction) if interaction else None,
                      "bootstrap_95_interval": interval(interaction, 2026101922) if len(interaction) >= 2 else None,
                      "units": "percentage_points"})

condition_medians = []
for workers, mode in conditions:
    rows = [per_arm[(block, workers, mode)] for block in blocks]
    for rail in rails_present:
        valid = [row["joules_per_output_token_by_named_rail"][rail] for row in rows
                 if row["status"] == "estimated" and rail in row["joules_per_output_token_by_named_rail"]]
        condition_medians.append({"workers": workers, "transfer": mode, "rail": rail,
                                  "estimated_blocks": len(valid),
                                  "median_joules_per_output_token": statistics.median(valid) if valid else None})

result = {
    "scope": "Separate named tegrastats rails integrated over each request window. Includes board idle/background, is not process-attributed, and rails are not summed.",
    "method": "Piecewise-linear integration of instantaneous mW at one-second wall timestamps; request windows require bracketing samples and reject gaps over 2.5 seconds.",
    "planned_windows": len(per_arm),
    "estimated_windows": sum(row["status"] == "estimated" for row in per_arm.values()),
    "unsupported_windows": sum(row["status"] != "estimated" for row in per_arm.values()),
    "condition_medians": condition_medians,
    "paired_contrasts": contrasts,
    "per_arm": list(per_arm.values()),
}
(ROOT / "rail-energy.json").write_text(json.dumps(result, indent=2) + "\n")
with (ROOT / "rail-energy-pairs.csv").open("w", newline="") as f:
    fields = ("block", "workers", "transfer", "output_tokens", "request_seconds", "status", "reason",
              "joules_by_named_rail", "joules_per_output_token_by_named_rail")
    writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(per_arm.values())
print(json.dumps({key: result[key] for key in ("estimated_windows", "unsupported_windows", "condition_medians", "paired_contrasts")}, indent=2))
