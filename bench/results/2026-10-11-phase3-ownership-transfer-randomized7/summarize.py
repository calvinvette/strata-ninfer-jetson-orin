#!/usr/bin/env python3
"""Summarize randomized transfer-path process blocks with paired bootstrap CIs."""
import json
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODES = ("pinned_copy", "mapped_host", "managed_sequential", "async_pool_copy")
LINE = re.compile(r"^(pinned_copy|mapped_host|managed_sequential|async_pool_copy) iterations=10 median_ms=([0-9.]+)", re.M)


def main() -> None:
    rows = []
    for index in range(1, 8):
        folder = ROOT / "process-reps" / f"rep{index}"
        text = (folder / "supervisor" / "stdout.txt").read_text()
        order = re.search(r"^randomized_mode_order=(.*)$", text, re.M).group(1).strip(",")
        timings = {name: float(ms) for name, ms in LINE.findall(text)}
        if set(timings) != set(MODES) or "checksum=PASS" not in text:
            raise SystemExit(f"rep{index}: missing timing or checksum pass")
        supervisor = json.loads((folder / "supervisor" / "result.json").read_text())
        if supervisor["status"] != "pass":
            raise SystemExit(f"rep{index}: supervisor status {supervisor['status']}")
        gpu_mhz, cpu_mhz = [], []
        for line in (folder / "supervisor" / "memory.jsonl").read_text().splitlines():
            clocks = json.loads(line).get("clock_observations", {})
            if clocks.get("gpu", {}).get("hz"):
                gpu_mhz.append(clocks["gpu"]["hz"] / 1e6)
            cpu_mhz.extend(v["hz"] / 1e6 for v in clocks.get("cpu", {}).values() if v.get("hz"))
        rows.append({"rep": index, "order": order.split(","), "timings_ms": timings,
                     "minimum_available_bytes": supervisor["minimum_available_bytes"],
                     "gpu_mhz_range": [min(gpu_mhz), max(gpu_mhz)] if gpu_mhz else None,
                     "cpu_mhz_range": [min(cpu_mhz), max(cpu_mhz)] if cpu_mhz else None})

    random.seed(20261011)
    comparisons = []
    for candidate, control in (("mapped_host", "pinned_copy"),
                               ("managed_sequential", "pinned_copy"),
                               ("async_pool_copy", "pinned_copy"),
                               ("mapped_host", "managed_sequential")):
        effects = [row["timings_ms"][candidate] / row["timings_ms"][control] - 1 for row in rows]
        boot = [statistics.median(random.choices(effects, k=len(effects))) for _ in range(100_000)]
        boot.sort()
        comparisons.append({"candidate": candidate, "control": control,
                            "paired_median_delta_percent": 100 * statistics.median(effects),
                            "bootstrap_95_percentile_interval_percent": [
                                100 * boot[int(.025 * (len(boot) - 1))],
                                100 * boot[int(.975 * (len(boot) - 1))]],
                            "paired_block_deltas_percent": [100 * value for value in effects]})
    summary = {"scope": "isolated 64 MiB transfer/checksum, not product-path performance",
               "n_process_blocks": len(rows), "rows": rows,
               "process_median_summary_ms": {
                   mode: {"median": statistics.median(row["timings_ms"][mode] for row in rows),
                          "minimum": min(row["timings_ms"][mode] for row in rows),
                          "maximum": max(row["timings_ms"][mode] for row in rows)} for mode in MODES},
               "comparisons": comparisons}
    (ROOT / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["process_median_summary_ms"], indent=2))
    print(json.dumps(summary["comparisons"], indent=2))


if __name__ == "__main__":
    main()
