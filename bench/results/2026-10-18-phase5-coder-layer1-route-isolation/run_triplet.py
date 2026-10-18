#!/usr/bin/env python3
"""Run randomized Coder CPU/mirror/one-layer-GPU route controls in fresh services."""
import json
import argparse
import hashlib
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--output", type=Path, required=True, help="new directory for this campaign")
ap.add_argument("--seed", type=int, default=20261019)
args = ap.parse_args()
ARMS = ("cpu_default", "cpu_mirror", "gpu_layer1")
SEED = args.seed
order = list(ARMS)
random.Random(SEED).shuffle(order)
campaign = {"schema": 1, "seed": SEED, "order": order,
            "design": "same 512-token prompt; MTP2; FP16 KV; no adaptive swaps; prompt cache off; same 3,000-slot capacity",
            "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
            "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
            "model_quantization": "IQ1_M",
            "binary_sha256": hashlib.sha256(Path("/home/calvin/workspace/strata-ninfer-jetson-orin/build/integration/candidate/strata").read_bytes()).hexdigest(),
            "profile_sha256": hashlib.sha256((HERE / "layer1-gpu-profile.bin").read_bytes()).hexdigest(),
            "status": "running", "runs": [], "started_wall_time_s": time.time()}
OUT = args.output if args.output.is_absolute() else ROOT / args.output
OUT.mkdir(exist_ok=False)
path = OUT / "campaign.json"
path.write_text(json.dumps(campaign, indent=2) + "\n")
for arm in order:
    target = OUT / arm
    target.mkdir()
    command = ["systemd-run", "--user", "--scope", "--collect", "-p", "MemoryMax=28G",
               "-p", "IOAccounting=yes", "/usr/bin/python3.12", str(ROOT / "tools/integration/run_control.py"),
               "--output", str((target / "supervisor").resolve()), "--timeout", "1200", "--interval", "1",
               "--sample-clocks", "--", sys.executable, str(HERE / "run_one.py"), "--arm", arm,
               "--output", str((target / "result").resolve())]
    run = {"arm": arm, "command": command, "status": "running"}
    campaign["runs"].append(run)
    path.write_text(json.dumps(campaign, indent=2) + "\n")
    with (target / "launch.txt").open("w") as log:
        rc = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    sup = target / "supervisor/result.json"
    if sup.exists():
        d = json.loads(sup.read_text())
        run.update({"status": d.get("status"), "returncode": rc,
                    "minimum_host_available_bytes": d.get("minimum_available_bytes"),
                    "minimum_admission_available_bytes": d.get("minimum_admission_available_bytes"),
                    "elapsed_s": d.get("elapsed_s"), "reason": d.get("reason")})
    else:
        run.update({"status": "fail", "returncode": rc, "reason": "supervisor result missing"})
    result = target / "result/requests.json"
    if result.exists():
        run["request"] = json.loads(result.read_text())
    path.write_text(json.dumps(campaign, indent=2) + "\n")
    print(f"finished {arm}: {run['status']}", flush=True)
campaign["status"] = "complete" if all(r["status"] == "pass" for r in campaign["runs"]) else "incomplete"
campaign["finished_wall_time_s"] = time.time()
path.write_text(json.dumps(campaign, indent=2) + "\n")
raise SystemExit(int(campaign["status"] != "complete"))
