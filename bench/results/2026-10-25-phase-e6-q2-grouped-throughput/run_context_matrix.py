#!/usr/bin/env python3
"""Run a guarded paired Q2_0 service screen across configured context sizes."""
import json
import hashlib
from pathlib import Path
import random
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
BASE_CONFIG = ROOT / "bench/results/2026-10-25-q2-current-candidate-performance/server-config.template.json"
REFERENCE_WORKLOADS = ROOT / "bench/results/2026-10-09-paired-api-controls/extension/block-3-workloads.json"
CONTEXTS = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def make_workloads():
    refs = json.loads(REFERENCE_WORKLOADS.read_text())["workloads"]
    by_name = {row["cell"]: row for row in refs}
    workloads = []
    names = ("pp512+tg64", "pp2048+tg128", "historical-repeat-32",
             "historical-repeat-128", "historical-repeat-256")
    for name in names:
        row = dict(by_name[name])
        if name.startswith("historical-repeat-"):
            row["cell"] = f"pp{row['prompt_tokens']}+tg64"
        workloads.append(row)
    return {"workloads": workloads}


def make_config(base, context, arm, out, port):
    config = json.loads(json.dumps(base))
    config["exe"] = str(ROOT / "build/integration/e0-cuda-build/strata")
    config["cwd"] = str(ROOT)
    config["args"][config["args"].index("--max-context") + 1] = str(context)
    if arm == "ninfer":
        config["args"] += ["--expert-backend", "ninfer", "--expert-backend-strict"]
    config["model_name"] = f"E6 Q2_0 {arm} ctx{context}"
    config["log"] = str((out / f"{arm}-engine.log").resolve())
    config["port"] = port
    config["env"] = {**config.get("env", {}), "STRATA_RESIDENCY_DUMP": str((out / f"{arm}-residency.csv").resolve())}
    return config


def compact_requests(path):
    """Keep metrics and output hashes while removing generated text and SSE payloads."""
    data = json.loads(path.read_text())
    for row in data.get("checks", []):
        response = row.get("response")
        if response:
            choices = response.pop("choices", [])
            content = "".join(choice.get("message", {}).get("content", "") for choice in choices)
            reasoning = "".join(choice.get("message", {}).get("reasoning_content", "") for choice in choices)
            row["output_sha256"] = hashlib.sha256((content + reasoning).encode()).hexdigest()
            row["response"] = {key: response[key] for key in ("usage", "timings") if key in response}
        observation = row.get("stream_observation")
        if observation and "events" in observation:
            observation["event_count"] = len(observation.pop("events"))
    write_json(path, data)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--contexts", type=int, nargs="+", default=CONTEXTS)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--seed", type=int, default=870126)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() and not args.resume:
        parser.error("output exists; pass --resume to continue")
    out.mkdir(parents=True, exist_ok=True)
    matrix_path = out / "matrix.json"
    matrix = json.loads(matrix_path.read_text()) if args.resume and matrix_path.exists() else {
        "date_started": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "hardware": "local Jetson AGX Orin, CUDA 12.6, SM87; no SSH",
        "binary": str(ROOT / "build/integration/e0-cuda-build/strata"),
        "model": "Coder Q2_0, matched 3,000-slot profile, FP16 KV, MTP off, prefill 128, workers 8",
        "contexts": [], "cells": [],
        "protocol": "one randomized NInfer/Strata pair per capacity; five natural-generation workload shapes; run_control six-GiB floor; each service independently supervised",
    }
    matrix["contexts"] = list(dict.fromkeys([*matrix["contexts"], *args.contexts]))
    save_cells = {(row["context"], row["arm"]): row for row in matrix["cells"]}
    base = json.loads(BASE_CONFIG.read_text())
    all_workloads = make_workloads()["workloads"]
    rng = random.Random(args.seed)
    failed_contexts = {row["context"] for row in matrix["cells"] if row["status"] != "pass"}
    for context in args.contexts:
        if context in failed_contexts:
            continue
        arms = ["strata", "ninfer"]
        rng.shuffle(arms)
        cell_root = out / str(context)
        workloads = {"workloads": [w for w in all_workloads
                                   if w["prompt_tokens"] + w["generate_tokens"] <= context]}
        write_json(cell_root / "workloads.json", workloads)
        pair_failed = False
        for arm in arms:
            existing = save_cells.get((context, arm))
            if existing and existing["status"] == "pass":
                continue
            cell = cell_root / arm
            cell.mkdir(parents=True, exist_ok=True)
            port = 18887
            config_path = cell / "server-config.json"
            write_json(config_path, make_config(base, context, arm, cell, port))
            request_file = cell / "requests.json"
            command = [
                sys.executable, str(ROOT / "tools/integration/run_control.py"),
                "--output", str(cell / "supervisor"), "--timeout", str(args.timeout),
                "--interval", "1", "--sample-clocks", "--",
                sys.executable, str(ROOT / "tools/integration/api_control_block.py"),
                "--config", str(config_path), "--workloads", str(cell_root / "workloads.json"),
                "--output", str(request_file), "--variant", "candidate" if arm == "ninfer" else "baseline",
                "--no-trace",
            ]
            print(f"start ctx={context} arm={arm}", flush=True)
            launcher = cell / "launcher.txt"
            with launcher.open("w") as stream:
                code = subprocess.call(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            sup_path = cell / "supervisor/result.json"
            sup = json.loads(sup_path.read_text()) if sup_path.exists() else {}
            result_path = cell / "requests.json"
            requests = json.loads(result_path.read_text()) if result_path.exists() else {}
            if result_path.exists():
                compact_requests(result_path)
                requests = json.loads(result_path.read_text())
            checks = requests.get("checks", [])
            request_pass = bool(checks) and all(row.get("status") == "pass" for row in checks)
            status = "pass" if code == 0 and sup.get("status") == "pass" and request_pass else "fail"
            row = {
                "context": context, "arm": arm, "status": status,
                "returncode": code, "minimum_available_bytes": sup.get("minimum_available_bytes"),
                "minimum_admission_available_bytes": sup.get("minimum_admission_available_bytes"),
                "supervisor": str(sup_path), "requests": str(result_path),
                "residency_sha256": None,
                "reason": sup.get("reason") or requests.get("error"),
            }
            map_path = cell / f"{arm}-residency.csv"
            if map_path.exists():
                row["residency_sha256"] = hashlib.sha256(map_path.read_bytes()).hexdigest()
            save_cells[(context, arm)] = row
            matrix["cells"] = list(save_cells.values())
            write_json(matrix_path, matrix)
            print(f"finish ctx={context} arm={arm} status={status}", flush=True)
            if status != "pass":
                pair_failed = True
        if pair_failed:
            failed_contexts.add(context)
            for later in args.contexts:
                if later <= context:
                    continue
                for arm in ("strata", "ninfer"):
                    if (later, arm) not in save_cells:
                        row = {"context": later, "arm": arm, "status": "not_run_after_capacity_failure"}
                        save_cells[(later, arm)] = row
            matrix["cells"] = list(save_cells.values())
            write_json(matrix_path, matrix)
            break
    matrix["date_updated"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    write_json(matrix_path, matrix)
    return int(any(row["status"] != "pass" for row in matrix["cells"] if row["context"] in args.contexts))


if __name__ == "__main__":
    raise SystemExit(main())
