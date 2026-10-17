#!/usr/bin/env python3
"""Integrate named tegrastats rails over each passing API request window."""
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from request_telemetry import rails_from_lines, window_energy
from summarize_controls import interval

HERE = Path(__file__).resolve().parent
campaign = json.loads((HERE / "campaign/campaign.json").read_text())
rows = []
for run in campaign["runs"]:
    if run["status"] != "pass":
        continue
    arm_dir = HERE / "campaign" / run["directory"]
    requests = json.loads((arm_dir / "requests.json").read_text())
    measured = [x for x in requests["checks"] if not x.get("warmup")]
    if len(measured) != 1 or measured[0]["status"] != "pass":
        raise RuntimeError(f"expected one passing measured request: {run['name']}")
    req = measured[0]
    mem = [json.loads(x) for x in (arm_dir / "supervisor/memory.jsonl").read_text().splitlines()]
    if not mem:
        raise RuntimeError(f"missing memory samples: {run['name']}")
    offset = mem[0]["wall_time_s"] - mem[0]["monotonic_s"]
    rails = rails_from_lines((arm_dir / "supervisor/tegrastats.txt").read_text().splitlines())
    estimate = window_energy(rails,
        req["request_start_monotonic_s"] + offset,
        req["request_end_monotonic_s"] + offset)
    row = {"block": run["block"], "kv": run["kv"], "workload": run["workload"],
           "window": run["window"], "run": run["name"], "request_status": estimate["status"],
           "request_seconds": req["request_end_monotonic_s"] - req["request_start_monotonic_s"],
           "output_tokens": run["metrics"]["completion_tokens"], "scope": estimate.get("scope"),
           "reason": estimate.get("reason"), "joules_by_named_rail": estimate.get("joules_by_named_rail", {})}
    row["joules_per_output_token_by_named_rail"] = {
        k: v / row["output_tokens"] for k, v in row["joules_by_named_rail"].items()}
    rows.append(row)

# Pair only exact block/KV/workload matched MTP-off and MTP4 arms.
pairs = []
for base in rows:
    if base["window"] != 0 or base["request_status"] != "estimated":
        continue
    cand = next((x for x in rows if x["block"] == base["block"] and x["kv"] == base["kv"]
                 and x["workload"] == base["workload"] and x["window"] == 4
                 and x["request_status"] == "estimated"), None)
    if not cand:
        continue
    common = set(base["joules_by_named_rail"]) & set(cand["joules_by_named_rail"])
    for rail in sorted(common):
        pairs.append({"block": base["block"], "kv": base["kv"], "workload": base["workload"],
                      "rail": rail, "mtp_off_j": base["joules_by_named_rail"][rail],
                      "mtp4_j": cand["joules_by_named_rail"][rail],
                      "mtp_off_j_per_output_token": base["joules_per_output_token_by_named_rail"][rail],
                      "mtp4_j_per_output_token": cand["joules_per_output_token_by_named_rail"][rail],
                      "mtp4_over_off_ratio": cand["joules_by_named_rail"][rail] / base["joules_by_named_rail"][rail]})

summary = {"schema": 1,
 "scope": "Named tegrastats rails integrated separately over API request wall windows. Includes board idle/background activity; not process-attributed and not a summed or whole-board energy measurement.",
 "method": "Piecewise-linear integration of one-second-granularity mW readings; requests without bracketing samples or with >2.5s gaps are unsupported.",
 "attempts": len(campaign["runs"]), "passing_request_windows": len(rows),
 "estimated_request_windows": sum(x["request_status"] == "estimated" for x in rows),
 "unsupported_request_windows": sum(x["request_status"] != "estimated" for x in rows),
 "request_estimates": rows, "paired_estimates": pairs, "paired_summaries": []}
for kv in ("fp16", "int8"):
  for workload in sorted({x["workload"] for x in rows}):
    for rail in sorted({x["rail"] for x in pairs}):
      values=[x["mtp4_over_off_ratio"] for x in pairs if x["kv"]==kv and x["workload"]==workload and x["rail"]==rail]
      if values:
        ci=interval(values, 20261017)
        selected=[x for x in pairs if x["kv"]==kv and x["workload"]==workload and x["rail"]==rail]
        summary["paired_summaries"].append({"kv":kv,"workload":workload,"rail":rail,
          "paired_blocks":len(values),"mtp_off_median_j":statistics.median(x["mtp_off_j"] for x in selected),
          "mtp4_median_j":statistics.median(x["mtp4_j"] for x in selected),
          "mtp_off_median_j_per_output_token":statistics.median(x["mtp_off_j_per_output_token"] for x in selected),
          "mtp4_median_j_per_output_token":statistics.median(x["mtp4_j_per_output_token"] for x in selected),
          "mtp4_over_off_median_percent_change":(statistics.median(values)-1)*100,
          "paired_bootstrap_95_interval_percent":[(ci[0]-1)*100,(ci[1]-1)*100]})
(HERE / "rail-energy.json").write_text(json.dumps(summary, indent=2) + "\n")
with (HERE / "rail-energy-pairs.csv").open("w", newline="") as f:
    fields=list(pairs[0]) if pairs else ["block","kv","workload","rail"]
    w=csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(pairs)
print(json.dumps({k:summary[k] for k in ("passing_request_windows","estimated_request_windows","unsupported_request_windows","paired_summaries")}, indent=2))
