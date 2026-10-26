#!/usr/bin/env python3
"""Randomized three-pair repeat of the corrected 4K/557+64 Q2_0 screen."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "bench/results/2026-10-25-phase-e6-q2-grouped-throughput"))
import run_context_matrix as context_matrix


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "campaign")
    ap.add_argument("--seed", type=int, default=20261025)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    base_workloads = json.loads((ROOT / "bench/results/2026-10-25-phase-e6-q2-grouped-throughput/fixed-swiglu-context-check/4096/workloads.json").read_text())
    workload = next(row for row in base_workloads["workloads"] if row["cell"] == "pp557+tg64")
    workloads_path = out / "workloads.json"
    write_json(workloads_path, {"workloads": [workload]})
    base = json.loads(context_matrix.BASE_CONFIG.read_text())
    rng = random.Random(args.seed)
    result = {"context": 4096, "cell": "pp557+tg64", "pairs": [],
              "binary": str(ROOT / "build/integration/e0-cuda-build/strata"),
              "protocol": "three randomized independent Strata/NInfer service pairs; one warmup and one measured request per fresh service"}
    for pair in range(1, 4):
        arms = ["strata", "ninfer"]
        rng.shuffle(arms)
        pair_result = {"pair": pair, "order": arms, "arms": {}}
        for arm in arms:
            cell = out / f"pair-{pair}" / arm
            cell.mkdir(parents=True, exist_ok=True)
            config_path = cell / "server-config.json"
            config = context_matrix.make_config(base, 4096, arm, cell, 18887)
            write_json(config_path, config)
            requests_path = cell / "requests.json"
            command = [
                sys.executable, str(ROOT / "tools/integration/run_control.py"),
                "--output", str(cell / "supervisor"), "--timeout", "1800",
                "--interval", "1", "--sample-clocks", "--",
                sys.executable, str(ROOT / "tools/integration/api_control_block.py"),
                "--config", str(config_path), "--workloads", str(workloads_path),
                "--output", str(requests_path), "--variant", "candidate" if arm == "ninfer" else "baseline",
                "--no-trace",
            ]
            launcher = cell / "launcher.txt"
            with launcher.open("w") as stream:
                code = subprocess.call(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            supervisor_path = cell / "supervisor/result.json"
            supervisor = json.loads(supervisor_path.read_text()) if supervisor_path.exists() else {}
            if requests_path.exists():
                context_matrix.compact_requests(requests_path)
                requests = json.loads(requests_path.read_text())
            else:
                requests = {}
            measured = [r for r in requests.get("checks", []) if not r.get("warmup")]
            map_path = Path(config["env"]["STRATA_RESIDENCY_DUMP"])
            status = "pass" if code == 0 and supervisor.get("status") == "pass" and len(measured) == 1 and measured[0].get("status") == "pass" else "fail"
            pair_result["arms"][arm] = {
                "status": status,
                "returncode": code,
                "supervisor": str(supervisor_path),
                "requests": str(requests_path),
                "minimum_available_bytes": supervisor.get("minimum_available_bytes"),
                "residency_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest() if map_path.exists() else None,
                "measured": measured[0] if measured else None,
            }
            if status != "pass":
                write_json(out / "results.json", result)
                return 1
            print(f"pair {pair}/3 {arm} complete", flush=True)
        result["pairs"].append(pair_result)
        write_json(out / "results.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
