#!/usr/bin/env python3
"""Validate and summarize independent Q8_1 scalar/NEON process runs."""
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sample_re = re.compile(r"^sample=(\d+) order=(\S+) scalar_ms=([0-9.]+) neon_ms=([0-9.]+) delta_pct=(-?[0-9.]+)$")
runs = []
for rep in range(1, 4):
    meta = json.loads((ROOT / f"rep-{rep:02d}.json").read_text())
    assert meta["returncode"] == 0
    lines = (ROOT / f"rep-{rep:02d}.txt").read_text().splitlines()
    samples = []
    for line in lines:
        m = sample_re.match(line)
        if m:
            samples.append({"sample": int(m[1]), "order": m[2], "scalar_ms": float(m[3]),
                            "neon_ms": float(m[4]), "neon_vs_scalar_pct": float(m[5])})
    assert len(samples) == 9
    final = lines[-1]
    assert "contract=Strata_Q8_1" in final and "mismatched_blocks=0" in final
    scalar = statistics.median(x["scalar_ms"] for x in samples)
    neon = statistics.median(x["neon_ms"] for x in samples)
    paired_sample_delta = statistics.median(x["neon_vs_scalar_pct"] for x in samples)
    delta = (neon / scalar - 1.0) * 100.0
    runs.append({"rep": rep, "seed": meta["seed"], "samples": samples,
                 "scalar_median_ms_per_16x256_rows": scalar,
                 "neon_median_ms_per_16x256_rows": neon,
                 "process_median_delta_pct": delta,
                 "median_paired_sample_delta_pct": paired_sample_delta,
                 "mismatched_blocks": 0})

scalar = [r["scalar_median_ms_per_16x256_rows"] for r in runs]
neon = [r["neon_median_ms_per_16x256_rows"] for r in runs]
delta = [r["process_median_delta_pct"] for r in runs]
out = {
    "scope": "test-only AArch64 NEON implementation of Strata's Q8_1 activation contract",
    "rows": 256, "width": 2560, "iterations_per_sample": 16,
    "samples_per_process": 9, "independent_processes": len(runs),
    "blocks_checked_per_process": 256 * (2560 // 32), "mismatched_blocks": 0,
    "median_of_process_medians_scalar_ms": statistics.median(scalar),
    "median_of_process_medians_neon_ms": statistics.median(neon),
    "median_of_process_median_deltas_pct": statistics.median(delta),
    "process_median_delta_values_pct": delta,
    "process_median_delta_range_pct": [min(delta), max(delta)],
    "runs": runs,
    "limits": [
        "operator timing only; not CPU expert dot, GPU, request or task-quality evidence",
        "three independent processes are a screening result, not a confidence interval",
        "dynamic clocks; no clock controls; EMC frequency inaccessible; energy not measured",
        "test-only source at this stage; production dispatch and defaults are unchanged",
    ],
}
(ROOT / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({k: out[k] for k in ("median_of_process_medians_scalar_ms",
    "median_of_process_medians_neon_ms", "median_of_process_median_deltas_pct",
    "process_median_delta_range_pct", "blocks_checked_per_process", "mismatched_blocks")}, indent=2))
