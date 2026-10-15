#!/usr/bin/env python3
"""Run seven randomized fresh-service pairs under separate memory scopes."""
import json
import argparse
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SEED = 20261016


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-name", default="campaign-retry2",
                        help="new output directory under this result (default: campaign-retry2)")
    args = parser.parse_args()
    campaign_root = HERE / args.campaign_name
    campaign_root.mkdir(exist_ok=False)
    launch_root = campaign_root / "launch-logs"
    launch_root.mkdir()
    order = []
    rng = random.Random(SEED)
    for block in range(7):
        variants = ["baseline", "candidate"]
        rng.shuffle(variants)
        order.extend({"block": block, "variant": variant} for variant in variants)
    record = {"seed": SEED, "planned_blocks": 7, "status": "running", "runs": []}
    campaign_path = campaign_root / "campaign.json"
    for item in order:
        block, variant = item["block"], item["variant"]
        config = HERE / ("config-mtp-off.json" if variant == "baseline" else "config-mtp3.json")
        workload = HERE / "workload" / "workload-8192.json"
        output_dir = campaign_root / f"block-{block:02d}-{variant}"
        request_output = output_dir / "requests.json"
        command = [
            "systemd-run", "--user", "--scope", "--collect",
            "-p", "MemoryMax=28G", "-p", "IOAccounting=yes",
            sys.executable, str(ROOT / "tools/integration/run_control.py"),
            "--output", str(output_dir), "--timeout", "1800", "--interval", "1",
            "--sample-clocks", "--", sys.executable,
            str(ROOT / "tools/integration/api_control_block.py"),
            "--config", str(config), "--workloads", str(workload),
            "--output", str(request_output), "--variant", variant,
            "--warmup-workloads", str(HERE / "warmup-workloads.json"), "--no-trace",
        ]
        run_record = {**item, "status": "running", "started_wall_time": time.time(),
                      "output_dir": str(output_dir.relative_to(ROOT)), "command": command}
        record["runs"].append(run_record)
        campaign_path.write_text(json.dumps(record, indent=2) + "\n")
        with (launch_root / f"block-{block:02d}-{variant}.txt").open("w") as log:
            completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        result_path = output_dir / "result.json"
        if result_path.exists():
            supervised = json.loads(result_path.read_text())
            run_record["supervisor_status"] = supervised.get("status")
            run_record["supervisor_returncode"] = supervised.get("returncode")
        run_record["returncode"] = completed.returncode
        run_record["finished_wall_time"] = time.time()
        run_record["status"] = "pass" if completed.returncode == 0 else "fail"
        run_record["reason"] = "command exit; response-quality and paired analysis separate"
        campaign_path.write_text(json.dumps(record, indent=2) + "\n")
        print(f"block={block} arm={variant} status={run_record['status']}", flush=True)
    record["status"] = "pass" if all(row["status"] == "pass" for row in record["runs"]) else "fail"
    campaign_path.write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
