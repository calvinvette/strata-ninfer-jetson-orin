#!/usr/bin/env python3
"""Run independent, one-warmup Q2_0 API performance blocks under run_control."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys
import time


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blocks", type=int, default=7)
    parser.add_argument("--seed", type=int, default=2026102501)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "campaign")
    parser.add_argument("--stop-after-first", action="store_true",
                        help="stop after block 0 for a launch/readiness review, then continue with --resume")
    parser.add_argument("--resume", action="store_true", help="continue a prior incomplete campaign in place")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.blocks < 1:
        parser.error("positive block count required")
    source = json.loads((root / "workloads.json").read_text())
    rng = random.Random(args.seed)
    campaign_path = args.output / "campaign.json"
    if args.resume:
        if not campaign_path.exists():
            parser.error("--resume requires an existing campaign.json")
        campaign = json.loads(campaign_path.read_text())
        if campaign.get("seed") != args.seed or campaign.get("planned_blocks") != args.blocks:
            parser.error("resume seed/block count must match the original campaign")
        rows = campaign["runs"]
        if campaign.get("finished_wall_time_s"):
            parser.error("campaign is already complete")
    else:
        if args.output.exists():
            parser.error("new campaign output directory required (use --resume for an existing campaign)")
        args.output.mkdir(parents=True)
        rows = []
        for block in range(args.blocks):
            workloads = list(source["workloads"])
            rng.shuffle(workloads)
            workload_path = args.output / f"block-{block:02d}-workloads.json"
            write(workload_path, {"workloads": workloads})
            rows.append({"block": block, "status": "not_run", "workloads": str(workload_path.resolve())})
        campaign = {"seed": args.seed, "planned_blocks": args.blocks,
                    "scope": "independent supervised server processes; one warmup then one measured request per workload; randomized workload order",
                    "runs": rows}
        write(campaign_path, campaign)

    for block, row in enumerate(rows):
        if row["status"] == "pass":
            continue
        if row["status"] not in ("not_run",):
            parser.error(f"block {block} is terminal ({row['status']}); investigate before resuming")
        workload_path = Path(row["workloads"])
        run_dir = args.output / f"block-{block:02d}"
        command = [
            sys.executable, str(root.parent.parent.parent / "tools/integration/run_control.py"),
            "--output", str((run_dir / "supervisor").resolve()), "--timeout", "3600",
            "--interval", "1", "--sample-clocks", "--",
            sys.executable, str(root.parent.parent.parent / "tools/integration/api_control_block.py"),
            "--config", str((root / "server-config.template.json").resolve()),
            "--workloads", str(workload_path.resolve()),
            "--output", str((run_dir / "requests.json").resolve()),
            "--variant", "candidate", "--rounds", "1", "--no-trace",
        ]
        row.update(command=command, started_wall_time_s=time.time())
        write(campaign_path, campaign)
        run_dir.mkdir()
        print(f"starting block-{block:02d}", flush=True)
        with (args.output / f"block-{block:02d}-launcher.txt").open("w") as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        result_path = run_dir / "supervisor/result.json"
        if result_path.exists():
            terminal = json.loads(result_path.read_text())
            row.update(status=terminal.get("status", "fail"), reason=terminal.get("reason"),
                       minimum_available_bytes=terminal.get("minimum_available_bytes"),
                       minimum_admission_available_bytes=terminal.get("minimum_admission_available_bytes"),
                       supervisor_returncode=code, result=str(result_path.resolve()))
        else:
            row.update(status="fail", reason="missing terminal supervisor result", supervisor_returncode=code)
        row["finished_wall_time_s"] = time.time()
        write(campaign_path, campaign)
        print(f"finished block-{block:02d}: {row['status']} {row.get('reason', '')}", flush=True)
        if row["status"] != "pass":
            for pending in rows[block + 1:]:
                pending["reason"] = "not launched after prior block failed or aborted"
            write(campaign_path, campaign)
            return 1
        if args.stop_after_first:
            campaign["first_block_review_pending"] = True
            write(campaign_path, campaign)
            return 0
    campaign["finished_wall_time_s"] = time.time()
    campaign.pop("first_block_review_pending", None)
    write(campaign_path, campaign)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
