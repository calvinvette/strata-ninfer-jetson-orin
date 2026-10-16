#!/usr/bin/env python3
"""Randomized paired recovery/state screen: GGML CPU route vs CUDA-mirror route."""
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/run_cpu_q8_1_route.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blocks", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20261019)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.blocks < 3 or args.output.exists():
        ap.error("use at least 3 blocks and a new output directory")
    args.output.mkdir(parents=True)
    rng = random.Random(args.seed)
    campaign = {"schema": 1, "seed": args.seed, "blocks": args.blocks,
                "factors": {"route": ["default GGML", "CUDA-mirror Q8_1"],
                            "adapt_every": 4, "adapt_swaps": 8, "prompt_cache": 0},
                "scope": "active accepted-only swaps; short/long/short/repeated-short state and output check; trace-enabled; not a timing experiment",
                "runs": [], "started_wall_time_s": time.time()}
    (args.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")

    for block in range(args.blocks):
        order = ["default", "cuda_mirror"]
        rng.shuffle(order)
        for route in order:
            name = f"block-{block:02d}-{route}"
            out = args.output / name
            runner_args = [sys.executable, str(RUNNER), "--adapt-every", "4",
                           "--adapt-swaps", "8", "--continuations", "1",
                           "--prompt-cache", "0"]
            if route == "cuda_mirror":
                runner_args.append("--cpu-q8-1-dot")
            runner_args += ["--output", str((out / "result").resolve())]
            cmd = [sys.executable, str(ROOT / "tools/integration/run_control.py"),
                   "--output", str((out / "supervisor").resolve()),
                   "--timeout", "1800", "--interval", "1", "--sample-clocks", "--",
                   *runner_args]
            (out).mkdir()
            row = {"block": block, "route": route, "directory": str(out.resolve()),
                   "command": cmd, "status": "not_run"}
            campaign["runs"].append(row)
            (args.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")
            with (out / "launch.txt").open("w") as log:
                code = subprocess.call(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            supervisor = out / "supervisor/result.json"
            if supervisor.exists():
                result = json.loads(supervisor.read_text())
                row.update(status=result.get("status"), returncode=code,
                           elapsed_s=result.get("elapsed_s"),
                           minimum_available_bytes=result.get("minimum_available_bytes"),
                           minimum_admission_available_bytes=result.get("minimum_admission_available_bytes"),
                           reason=result.get("reason"))
            else:
                row.update(status="fail", returncode=code, reason="missing supervisor result")
            analysis = out / "result/analysis.json"
            if analysis.exists():
                row["analysis"] = json.loads(analysis.read_text())
            (args.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")
            print(f"finished {name}: {row['status']}", flush=True)
    campaign["finished_wall_time_s"] = time.time()
    (args.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")
    return int(any(run["status"] != "pass" for run in campaign["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
