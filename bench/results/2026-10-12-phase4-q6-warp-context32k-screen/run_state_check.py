#!/usr/bin/env python3
"""Run one supervised, trace-enabled baseline/candidate pair for state parity."""
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "serve/server.py").exists())
HERE = Path(__file__).resolve().parent
ORDER = ["baseline", "candidate"]
random.Random(2026101233).shuffle(ORDER)
(HERE / "state-check/order.json").write_text(json.dumps({"seed": 2026101233, "order": ORDER}, indent=2) + "\n")
rows = []
for arm in ORDER:
    run = HERE / "state-check" / arm
    run.mkdir(exist_ok=True)
    command = [sys.executable, str(ROOT / "tools/integration/run_control.py"),
               "--output", str((run / "supervisor").resolve()), "--interval", "0.5",
               "--timeout", "1800", "--", sys.executable,
               str(ROOT / "tools/integration/api_control_block.py"),
               "--config", str((HERE / f"state-check/{arm}-config.json").resolve()),
               "--workloads", str((HERE / "state-check/workloads.json").resolve()),
               "--warmup-workloads", str((HERE / "state-check/warmup-workloads.json").resolve()),
               "--output", str((run / "requests.json").resolve()), "--variant", arm]
    with (run / "supervisor-console.txt").open("w") as log:
        rc = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    result_path = run / "supervisor/result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    rows.append({"arm": arm, "returncode": rc, "status": result.get("status"),
                 "minimum_available_bytes": result.get("minimum_available_bytes")})
    (HERE / "state-check/runs.json").write_text(json.dumps(rows, indent=2) + "\n")
    if rc != 0 or result.get("status") != "pass":
        raise SystemExit(f"{arm} failed; retained artifacts in {run}")
