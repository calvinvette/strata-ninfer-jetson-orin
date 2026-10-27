#!/usr/bin/env python3
"""Randomized Q2_0 paired screen for CPU-miss or staged compute backends."""
import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE_CONFIG = ROOT / "bench/results/2026-10-25-q2-current-candidate-performance/server-config.template.json"
REFERENCE_WORKLOADS = ROOT / "bench/results/2026-10-09-paired-api-controls/extension/block-3-workloads.json"
ARMS = ("cpu-miss", "ninfer-staged")
CONTEXT = 8192
SEED = 20261029
CAPTURE_TEXT = False
CAPTURE_STATE = False


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def workloads():
    refs = json.loads(REFERENCE_WORKLOADS.read_text())["workloads"]
    by_name = {row["cell"]: row for row in refs}
    names = ("pp512+tg64", "pp2048+tg128", "historical-repeat-32",
             "historical-repeat-128", "historical-repeat-256")
    rows = []
    for name in names:
        row = copy.deepcopy(by_name[name])
        if name.startswith("historical-repeat-"):
            row["cell"] = f"pp{row['prompt_tokens']}+tg64"
        rows.append(row)
    return {"workloads": rows}


def config_for(base, arm, cell):
    cfg = copy.deepcopy(base)
    cfg["exe"] = str(ROOT / "build/integration/e0-cuda-build/strata")
    cfg["cwd"] = str(ROOT)
    cfg["model_name"] = f"E6 Q2_0 {arm} staged workload screen"
    cfg["log"] = str((cell / "engine.log").resolve())
    cfg["port"] = 18884
    args = cfg["args"]
    args[args.index("--max-context") + 1] = str(CONTEXT)
    args[args.index("--pcie-frac") + 1] = "0.0" if arm == "cpu-miss" else "1.0"
    args += ["--resident-budget-gib", "6"]
    if arm == "ninfer-staged":
        args += ["--expert-backend", "ninfer", "--expert-backend-strict"]
    cfg["env"] = {
        **cfg.get("env", {}),
        "CUDA_MODULE_LOADING": "EAGER",
        "STRATA_RESIDENT_HEADROOM_GIB": "9",
        "STRATA_RESIDENCY_DUMP": str((cell / "residency.csv").resolve()),
    }
    if CAPTURE_STATE:
        cfg["env"]["STRATA_STATE_HASH"] = "1"
    return cfg


def run_arm(base, workload_path, block, arm, position):
    cell = OUT / f"pair-{block}" / arm
    cell.mkdir(parents=True, exist_ok=False)
    cfg_path = cell / "server-config.json"
    write_json(cfg_path, config_for(base, arm, cell))
    request_path = cell / "requests.json"
    command = [
        sys.executable, str(ROOT / "tools/integration/run_control.py"),
        "--output", str(cell / "supervisor"), "--timeout", "3600",
        "--interval", "1", "--sample-clocks", "--",
        sys.executable, str(ROOT / "tools/integration/api_control_block.py"),
        "--config", str(cfg_path), "--workloads", str(workload_path),
        "--output", str(request_path),
        "--variant", "candidate" if arm == "ninfer-staged" else "baseline",
    ]
    command.append("--no-trace")
    if CAPTURE_STATE:
        command.append("--state-hash")
    launcher = cell / "launcher.txt"
    started = time.time()
    with launcher.open("w") as log:
        code = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    requests = json.loads(request_path.read_text()) if request_path.exists() else {}
    for row in requests.get("checks", []):
        response = row.get("response")
        if response:
            choices = response.pop("choices", [])
            content = "".join(choice.get("message", {}).get("content", "") for choice in choices)
            reasoning = "".join(choice.get("message", {}).get("reasoning_content", "") for choice in choices)
            row["output_sha256"] = hashlib.sha256((content + reasoning).encode()).hexdigest()
            if CAPTURE_TEXT:
                suffix = "warmup" if row.get("warmup") else f"round-{row.get('round', 0)}"
                (cell / f"{row.get('cell')}-{suffix}.txt").write_text(content + reasoning)
            row["response"] = {key: response[key] for key in ("usage", "timings") if key in response}
        observation = row.get("stream_observation")
        if observation and "events" in observation:
            observation["event_count"] = len(observation.pop("events"))
    if request_path.exists():
        write_json(request_path, requests)
    supervisor_path = cell / "supervisor" / "result.json"
    supervisor = json.loads(supervisor_path.read_text()) if supervisor_path.exists() else {}
    residency = cell / "residency.csv"
    checks = requests.get("checks", [])
    status = "pass" if code == 0 and supervisor.get("status") == "pass" and checks and all(
        row.get("status") == "pass" for row in checks) else "fail"
    result = {
        "block": block, "position": position, "arm": arm, "status": status,
        "returncode": code, "started_unix": started,
        "minimum_available_bytes": supervisor.get("minimum_available_bytes"),
        "minimum_admission_available_bytes": supervisor.get("minimum_admission_available_bytes"),
        "residency_sha256": hashlib.sha256(residency.read_bytes()).hexdigest() if residency.exists() else None,
        "checks": [{key: row.get(key) for key in ("cell", "round", "warmup", "status", "reason",
                                                      "output_sha256", "response", "stream_observation",
                                                      "client_elapsed_s") if key in row}
                   for row in checks],
        "supervisor": str(supervisor_path), "launcher": str(launcher),
    }
    write_json(cell / "result.json", result)
    return result


def main():
    global OUT
    global CAPTURE_TEXT
    global CAPTURE_STATE
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT, help="campaign output directory")
    parser.add_argument("--only-workload", help="run one named workload cell")
    parser.add_argument("--pairs", type=int, default=3)
    parser.add_argument("--capture-text", action="store_true", help="save generated output text for mismatch diagnosis")
    parser.add_argument("--capture-state", action="store_true", help="enable final persistent-state fingerprints; diagnostic timing only")
    parser.add_argument("--comparison", choices=("cpu-miss-staged", "staged-compute"),
                        default="cpu-miss-staged",
                        help="compare CPU miss vs staged NInfer, or Strata vs NInfer compute with identical staging")
    args = parser.parse_args()
    OUT = args.out.resolve()
    CAPTURE_TEXT = args.capture_text
    CAPTURE_STATE = args.capture_state
    ARMS = (("cpu-miss", "ninfer-staged") if args.comparison == "cpu-miss-staged"
            else ("strata-staged", "ninfer-staged"))
    OUT.mkdir(parents=True, exist_ok=True)
    workload_set = workloads()
    if args.only_workload:
        workload_set["workloads"] = [row for row in workload_set["workloads"] if row["cell"] == args.only_workload]
        if not workload_set["workloads"]:
            parser.error(f"unknown workload cell: {args.only_workload}")
    (OUT / "workloads.json").write_text(json.dumps(workload_set, indent=2) + "\n")
    base = json.loads(BASE_CONFIG.read_text())
    matrix = {
        "date_started": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "binary_sha256": hashlib.sha256((ROOT / "build/integration/e0-cuda-build/strata").read_bytes()).hexdigest(),
        "model": "Qwen3.8-Flash-Next-GSQ-RCO-Q2_0; 3,000 expert slots; 6-GiB resident budget; 3-GiB workspace reserve; 8K capacity; MTP-2; prefill 128; 8 workers",
        "comparison": ("CPU miss fallback (pcie-frac 0) versus strict NInfer staged misses (pcie-frac 1)"
                       if args.comparison == "cpu-miss-staged" else
                       "Strata grouped compute versus strict NInfer grouped compute (pcie-frac 1 in both arms); "
                       "identical staged residency and workload required"),
        "screen": f"{args.pairs} randomized process pair(s); workload-level output hashes and API token counts checked; supervisor retains physical/admission memory and clock telemetry",
        "state_capture": "final persistent-state hashes enabled; timing is diagnostic only" if CAPTURE_STATE else None,
        "seed": SEED, "contexts": [CONTEXT], "pairs": [],
    }
    write_json(OUT / "matrix.json", matrix)
    rng = random.Random(SEED)
    for block in range(1, args.pairs + 1):
        order = list(ARMS)
        rng.shuffle(order)
        pair = []
        for position, arm in enumerate(order, 1):
            result = run_arm(base, OUT / "workloads.json", block, arm, position)
            pair.append(result)
            write_json(OUT / "matrix.json", matrix)
            print(json.dumps({"block": block, "arm": arm, "status": result["status"],
                              "min_available": result["minimum_available_bytes"]}), flush=True)
            if result["status"] != "pass":
                raise SystemExit(f"stopped on failed arm: pair {block} {arm}")
        hashes = {row["residency_sha256"] for row in pair}
        if len(hashes) != 1:
            raise SystemExit(f"pair {block} resident-map mismatch: {sorted(hashes)}")
        matrix["pairs"].append({"block": block, "order": order, "resident_map_sha256": next(iter(hashes)),
                                "arms": [row["arm"] for row in pair]})
        write_json(OUT / "matrix.json", matrix)
    matrix["date_updated"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    write_json(OUT / "matrix.json", matrix)


if __name__ == "__main__":
    main()
