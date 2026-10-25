#!/usr/bin/env python3
"""Execute the current-port context-capacity matrix one guarded cell at a time."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
CONTEXTS = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]
MODELS = ["coder-iq1m", "coder-q2_0", "original-iq3_s"]


def save(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument("--contexts", nargs="+", type=int, default=CONTEXTS)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=86400)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() and not args.resume:
        parser.error("output exists; use --resume")
    out.mkdir(parents=True, exist_ok=True)
    matrix_path = out / "matrix.json"
    if args.resume:
        matrix = json.loads(matrix_path.read_text())
        matrix["contexts"] = list(dict.fromkeys([*matrix.get("contexts", []), *args.contexts]))
        matrix["models"] = list(dict.fromkeys([*matrix.get("models", []), *args.models]))
    else:
        matrix = {
            "date_started": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "hardware": "local Jetson AGX Orin; no SSH",
            "binary": str(ROOT / "build/integration/candidate/strata"),
            "contexts": args.contexts,
            "models": args.models,
            "prompt_repeat_counts": [32, 128, 256],
            "rounds_per_prompt": 3,
            "output_tokens": 64,
            "cache_policy": "model-specific fixed profile flags retained across all context capacities; only --max-context varies",
            "resource_policy": "one cell at a time; run_control six-GiB physical/admission floor; systemd scope MemoryMax=28G; do not continue above first failed context for a model",
            "cells": [],
        }
        save(matrix_path, matrix)
    existing = {(r["model"], r["context"]): r for r in matrix["cells"]}
    for model in args.models:
        stopped = False
        for context in args.contexts:
            if (model, context) in existing:
                status = existing[(model, context)]["status"]
                if status == "passed":
                    continue
                if status in ("pressure_abort", "failed", "timed_out", "service_start_failed"):
                    stopped = True
                    continue
            if stopped:
                if (model, context) not in existing:
                    row = {"model": model, "context": context, "status": "not_run_after_prior_capacity_failure"}
                    matrix["cells"].append(row)
                    save(matrix_path, matrix)
                continue
            cell = out / model / str(context)
            supervisor = cell / "supervisor"
            command = [
                "systemd-run", "--user", "--scope", "--collect",
                "-p", "MemoryMax=28G", "-p", "IOAccounting=yes",
                sys.executable, str(ROOT / "tools/integration/run_control.py"),
                "--output", str(supervisor), "--timeout", str(args.timeout),
                "--interval", "1", "--sample-clocks", "--",
                sys.executable, str(Path(__file__).resolve().with_name("run_cell.py")),
                "--model", model, "--context", str(context), "--out", str(cell / "run"),
            ]
            cell.mkdir(parents=True, exist_ok=True)
            started = time.time()
            print(f"launch {model} context={context}", flush=True)
            launcher_path = cell / "launcher.txt"
            with launcher_path.open("w") as log:
                code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
            supervisor_result = supervisor / "result.json"
            sup = json.loads(supervisor_result.read_text()) if supervisor_result.exists() else {}
            run_result = cell / "run/cell.json"
            run_data = json.loads(run_result.read_text()) if run_result.exists() else {}
            status = "passed" if code == 0 and sup.get("status") == "pass" and run_data.get("status") == "passed" else sup.get("status", "failed")
            row = {
                "model": model,
                "context": context,
                "status": status,
                "returncode": code,
                "started_wall_time": started,
                "finished_wall_time": time.time(),
                "minimum_available_bytes": sup.get("minimum_available_bytes"),
                "minimum_admission_available_bytes": sup.get("minimum_admission_available_bytes"),
                "supervisor": str(supervisor_result),
                "run": str(run_result),
                "reason": sup.get("reason") or run_data.get("error"),
            }
            if (model, context) in existing:
                matrix["cells"] = [r for r in matrix["cells"] if (r["model"], r["context"]) != (model, context)]
            matrix["cells"].append(row)
            existing[(model, context)] = row
            save(matrix_path, matrix)
            print(f"finished {model} context={context}: {status}", flush=True)
            if status != "passed":
                stopped = True
    matrix["date_updated"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    save(matrix_path, matrix)
    return 0 if all(r["status"] == "passed" for r in matrix["cells"] if r.get("model") in args.models) else 1


if __name__ == "__main__":
    raise SystemExit(main())
