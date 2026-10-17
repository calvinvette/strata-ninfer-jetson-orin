#!/usr/bin/env python3
"""Randomized paired all-layer MoE activation trace around a known divergence."""
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
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--adapt-every", type=int, default=4)
    ap.add_argument("--adapt-swaps", type=int, default=8)
    ap.add_argument("--capture-cpu-outputs", action="store_true",
                    help="capture actual CPU-owned expert rows at dispatch 1393/layer 1")
    ap.add_argument("--capture-combined-moe", action="store_true",
                    help="capture verifier layer-1 weighted-combine outputs")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.adapt_every < 0 or args.adapt_swaps < 0 or ((args.adapt_every == 0) != (args.adapt_swaps == 0)):
        ap.error("disable adaptation with both --adapt-every 0 and --adapt-swaps 0, or set both positive")
    if args.output.exists():
        ap.error("choose a new output directory")
    args.output.mkdir(parents=True)
    order = ["default", "cuda_mirror"]
    random.Random(args.seed).shuffle(order)
    campaign = {
        "schema": 1,
        "seed": args.seed,
        "order": order,
        "factors": {"route": ["default GGML", "CUDA-mirror Q8_1"],
                    "adapt_every": args.adapt_every, "adapt_swaps": args.adapt_swaps,
                    "prompt_cache": 0},
        "capture": {"layer": -1, "start_row": 1392, "rows": 192,
                    "reason": "bounded dispatch window around the selected layer-1 route point"},
        "capture_cpu_outputs": args.capture_cpu_outputs,
        "capture_combined_moe": args.capture_combined_moe,
        "scope": "one paired diagnostic; bounded all-layer activations around a selected route point; no timing claim",
        "runs": [],
        "started_wall_time_s": time.time(),
    }
    path = args.output / "campaign.json"
    path.write_text(json.dumps(campaign, indent=2) + "\n")
    for route in order:
        out = args.output / route
        out.mkdir()
        runner_args = [sys.executable, str(RUNNER), "--adapt-every", str(args.adapt_every),
                       "--adapt-swaps", str(args.adapt_swaps), "--continuations", "1",
                       "--prompt-cache", "0", "--capture-layer", "-1",
                       "--capture-start-row", "1392", "--capture-rows", "192"]
        if args.capture_cpu_outputs:
            runner_args += ["--capture-cpu-output", "--capture-output-layer", "1",
                            "--capture-dispatch", "1393"]
        if args.capture_combined_moe:
            runner_args.append("--capture-combined-moe")
        if route == "cuda_mirror":
            runner_args.append("--cpu-q8-1-dot")
        runner_args += ["--output", str((out / "result").resolve())]
        cmd = [sys.executable, str(ROOT / "tools/integration/run_control.py"),
               "--output", str((out / "supervisor").resolve()), "--timeout", "1800",
               "--interval", "1", "--sample-clocks", "--", *runner_args]
        row = {"route": route, "command": cmd, "status": "not_run"}
        campaign["runs"].append(row)
        path.write_text(json.dumps(campaign, indent=2) + "\n")
        with (out / "launch.txt").open("w") as log:
            code = subprocess.call(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        supervisor = out / "supervisor/result.json"
        analysis = out / "result/analysis.json"
        if supervisor.exists():
            result = json.loads(supervisor.read_text())
            row.update(status=result.get("status"), returncode=code,
                       elapsed_s=result.get("elapsed_s"),
                       minimum_available_bytes=result.get("minimum_available_bytes"),
                       minimum_admission_available_bytes=result.get("minimum_admission_available_bytes"),
                       reason=result.get("reason"))
        else:
            row.update(status="fail", returncode=code, reason="missing supervisor result")
        if analysis.exists():
            row["analysis"] = json.loads(analysis.read_text())
        path.write_text(json.dumps(campaign, indent=2) + "\n")
        print(f"finished {route}: {row['status']}", flush=True)
    campaign["finished_wall_time_s"] = time.time()
    path.write_text(json.dumps(campaign, indent=2) + "\n")
    return int(any(run["status"] != "pass" for run in campaign["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
