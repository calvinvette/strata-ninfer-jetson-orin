import json
import random
import subprocess
import sys
from pathlib import Path

root = next(p for p in Path(__file__).resolve().parents if (p / "serve/server.py").exists())
base = root / "bench/results/2026-10-12-phase3-q2-graph-context64k-spec4"
template = json.loads((base / "repeat1/server-config.json").read_text())
probe = base / "run_graph_probe.py"
control = root / "tools/integration/run_control.py"
out = base / "capture-mode-comparison"
out.mkdir(exist_ok=True)
rng = random.Random(20261012)
arms = ["capture", "no_capture"] * 3
rng.shuffle(arms)
(out / "order.json").write_text(json.dumps({"seed": 20261012, "order": arms}, indent=2) + "\n")
rows = []

for i, arm in enumerate(arms, 1):
    run = out / f"run{i:02d}-{arm}"
    run.mkdir(exist_ok=True)
    cfg = dict(template)
    cfg["port"] = 19100 + i
    cfg["log"] = str((run / "engine.log").resolve())
    cfg["args"] = list(template["args"])
    if arm == "no_capture":
        cfg["args"].append("--no-capture")
    (run / "server-config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    cmd = [sys.executable, str(control), "--output", str((run / "supervisor").resolve()),
           "--interval", "0.5", "--timeout", "600", "--", sys.executable,
           str(probe), str(run.resolve())]
    completed = subprocess.run(cmd, cwd=root)
    result_file = run / "supervisor/result.json"
    result = json.loads(result_file.read_text()) if result_file.exists() else {}
    rows.append({"index": i, "arm": arm, "returncode": completed.returncode,
                 "status": result.get("status"), "minimum_available_bytes": result.get("minimum_available_bytes"),
                 "run": str(run.relative_to(root))})
    (out / "runs.json").write_text(json.dumps(rows, indent=2) + "\n")
    if completed.returncode != 0:
        raise SystemExit(f"run {i} failed; retained at {run}")
