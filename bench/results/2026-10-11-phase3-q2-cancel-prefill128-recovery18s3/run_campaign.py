#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
for i in range(3):
    run = OUT / f"run-{i:02d}"
    run.mkdir(exist_ok=False)
    command = [sys.executable, "tools/integration/run_control.py", "--output", str(run / "supervisor"),
               "--interval", "0.5", "--timeout", "1800", "--sample-clocks", "--",
               sys.executable, "tools/integration/cancel_long_prefill_recovery.py",
               "--config", str(OUT / f"config-{i:02d}.json"),
               "--long-workload", str(ROOT / "bench/results/2026-10-09-phase3-fullchunk-2048/workloads.json"),
               "--output", str(run / "result.json"), "--cancel-after-s", "18.0"]
    log = run / "launch.log"
    with log.open("w") as f:
        f.write(json.dumps({"run": i, "command": command}) + "\n"); f.flush()
        rc = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
        f.write(f"\nreturncode={rc}\n"); f.flush()
    print(f"run {i}: returncode={rc}", flush=True)
