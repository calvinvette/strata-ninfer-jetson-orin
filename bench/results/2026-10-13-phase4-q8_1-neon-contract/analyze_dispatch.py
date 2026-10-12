#!/usr/bin/env python3
"""Analyze paired processes using the integrated opt-in Q8_1 path."""
import json
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
result_re = re.compile(r"^mode=(scalar|neon) seed=(\d+) median_ms_per_16x256=([0-9.]+)$")
pairs = []
for pair in range(1, 8):
    meta = json.loads((ROOT / f"dispatch-confirm-pair-{pair:02d}.json").read_text())
    medians = {}
    for mode in ("scalar", "neon"):
        lines = (ROOT / f"dispatch-confirm-pair-{pair:02d}-{mode}.txt").read_text().splitlines()
        match = result_re.match(lines[-1])
        assert match and match[1] == mode and int(match[2]) == meta["seed"]
        samples = [float(x.rsplit("=", 1)[1]) for x in lines[:-1]]
        assert len(samples) == 9
        medians[mode] = float(match[3])
    delta = (medians["neon"] / medians["scalar"] - 1.0) * 100.0
    pairs.append({"pair": pair, "seed": meta["seed"], "order": meta["order"],
                  "scalar_median_ms": medians["scalar"], "neon_median_ms": medians["neon"],
                  "neon_vs_scalar_delta_pct": delta, "samples_per_arm": 9})
deltas = [p["neon_vs_scalar_delta_pct"] for p in pairs]
boot_rng = random.Random(0x20261013)
boot = [statistics.median(boot_rng.choices(deltas, k=len(deltas))) for _ in range(20000)]
boot.sort()
out = {
    "scope": "production act_quant_q8_1 dispatch, STRATA_Q8_1_NEON=1 versus default scalar",
    "independent_paired_processes": len(pairs), "timing_samples_per_process_arm": 9,
    "median_of_pair_deltas_pct": statistics.median(deltas),
    "pair_delta_range_pct": [min(deltas), max(deltas)], "pairs": pairs,
    "paired_bootstrap_95pct_ci_median_delta_pct": [boot[499], boot[19499]],
    "limits": [
        "operator-only timing, not CPU expert/GPU/request/quality evidence",
        "three randomized process pairs are a screen, not a confidence interval",
        "clocks dynamic; EMC inaccessible; energy not measured",
    ],
}
(ROOT / "dispatch-analysis.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({k: out[k] for k in ("median_of_pair_deltas_pct", "pair_delta_range_pct", "pairs")}, indent=2))
