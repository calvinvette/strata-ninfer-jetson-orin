#!/usr/bin/env python3
"""Run randomized paired controls with a fresh 28-GiB scope per arm."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools/integration"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-config", type=Path, required=True)
    ap.add_argument("--candidate-config", type=Path, required=True)
    ap.add_argument("--workloads", type=Path, required=True)
    ap.add_argument("--warmup-workloads", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--blocks", type=int, default=3)
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()
    if args.blocks < 3:
        ap.error("screen requires at least three independent paired blocks")
    if args.output.exists():
        ap.error("output already exists")
    for path in (args.baseline_config, args.candidate_config, args.workloads,
                 args.warmup_workloads):
        if not path.is_file():
            ap.error(f"missing input: {path}")

    args.output.mkdir(parents=True)
    workload_data = json.loads(args.workloads.read_text())
    rng = random.Random(args.seed)
    rows = []
    for block in range(args.blocks):
        variants = ["baseline", "candidate"]
        rng.shuffle(variants)
        ordered = dict(workload_data)
        ordered["workloads"] = list(workload_data["workloads"])
        rng.shuffle(ordered["workloads"])
        workload_path = args.output / f"block-{block}-workloads.json"
        workload_path.write_text(json.dumps(ordered, indent=2) + "\n")
        for variant in variants:
            rows.append({"block": block, "variant": variant, "status": "not_run",
                         "workloads": str(workload_path.resolve())})

    campaign = {
        "schema": 1,
        "design": "randomized paired model-quantization screen; each independent arm has its own 28-GiB memory scope",
        "seed": args.seed,
        "planned_blocks": args.blocks,
        "baseline_config": str(args.baseline_config.resolve()),
        "candidate_config": str(args.candidate_config.resolve()),
        "workloads": str(args.workloads.resolve()),
        "warmup_workloads": str(args.warmup_workloads.resolve()),
        "scope": "independent fresh loopback service per arm; distinct warmup; six-GiB host/effective-admission floor; no tracing; observed clocks only",
        "started_wall_time_s": time.time(),
        "runs": rows,
    }
    manifest = args.output / "campaign.json"

    def save() -> None:
        manifest.write_text(json.dumps(campaign, indent=2) + "\n")

    save()
    for index, row in enumerate(rows):
        variant = row["variant"]
        config = args.baseline_config if variant == "baseline" else args.candidate_config
        run_dir = args.output / f"block-{row['block']}-{variant}"
        command = [sys.executable, str(TOOLS / "run_control.py"), "--output",
                   str(run_dir.resolve()), "--timeout", "1800", "--interval", "1",
                   "--sample-clocks", "--", sys.executable,
                   str(TOOLS / "api_control_block.py"), "--config", str(config.resolve()),
                   "--workloads", row["workloads"], "--output",
                   str((run_dir / "requests.json").resolve()), "--variant", variant,
                   "--warmup-workloads", str(args.warmup_workloads.resolve()), "--no-trace"]
        scoped = ["systemd-run", "--user", "--scope", "--collect", "-p",
                  "MemoryMax=28G", "-p", "IOAccounting=yes", *command]
        row.update(command=scoped, reason="running; incomplete until supervisor terminal result")
        save()
        print("starting", run_dir.name, flush=True)
        with (args.output / f"{run_dir.name}-wrapper.txt").open("w") as log:
            wrapper_code = subprocess.call(scoped, cwd=ROOT, stdout=log,
                                            stderr=subprocess.STDOUT)
        result_path = run_dir / "result.json"
        if result_path.exists():
            terminal = json.loads(result_path.read_text())
            row.update(status=terminal["status"], supervisor_returncode=wrapper_code,
                       reason=terminal.get("reason"),
                       minimum_available_bytes=terminal.get("minimum_available_bytes"),
                       minimum_admission_available_bytes=terminal.get("minimum_admission_available_bytes"),
                       elapsed_s=terminal.get("elapsed_s"))
        else:
            row.update(status="fail", supervisor_returncode=wrapper_code,
                       reason="missing terminal run_control record")
        save()
        print("finished", run_dir.name, row["status"], row["reason"], flush=True)
        if row["status"] != "pass" or wrapper_code != 0:
            for pending in rows[index + 1:]:
                pending["reason"] = "not launched after failed/pressure-aborted arm"
            save()
            return 1
    campaign["finished_wall_time_s"] = time.time()
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
