#!/usr/bin/env python3
"""Run randomized fresh-service pairs for the Q2_0 MTP × workload design."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from campaign_plan import make_schedule, workload_filename

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUN_LOCK = Path("/tmp") / f"strata-integration-{os.getuid()}.lock"
SOURCE_COMMIT = "c55e84756e5497e1e1fd9805e815db5859dfa959"
EXPECTED_BINARY_SHA256 = "57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_args(args):
    result = []
    index = 0
    while index < len(args):
        if args[index] in ("--mtp", "--mtp-max-t"):
            index += 2
        elif args[index] == "--spec":
            result.extend(("--spec", "{window}"))
            index += 2
        else:
            result.append(args[index])
            index += 1
    return result


def verify_config_pair(configs):
    baseline, candidate = configs["baseline"], configs["candidate"]
    for key in ("exe", "cwd", "tokenizer", "draft_vocab", "env", "cuda", "lib_dirs",
                "host", "port", "model_name", "log", "open_browser"):
        if baseline.get(key) != candidate.get(key):
            raise ValueError(f"paired configs differ outside MTP: {key}")
    if canonical_args(baseline["args"]) != canonical_args(candidate["args"]):
        raise ValueError("engine arguments differ outside MTP and verifier window")
    exe = Path(baseline["exe"])
    if not exe.is_file():
        raise FileNotFoundError(exe)
    actual = sha256(exe)
    if actual != EXPECTED_BINARY_SHA256:
        raise ValueError(f"candidate binary identity changed: {actual}")
    return actual


def verify_model_checksums():
    for line in (HERE / "model-checksums.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        expected, raw_path = line.split(None, 1)
        path = Path(raw_path.strip())
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"missing or changed model artifact: {path}")


def require_campaign_lock_free():
    with RUN_LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("another supervised Orin run currently owns the campaign lock") from error
        fcntl.flock(lock, fcntl.LOCK_UN)


def verify_artifacts_while_idle():
    # Hashing multi-gigabyte GGUFs is I/O activity; do not do it beside a live
    # inference campaign or while another supervised run owns the board.
    with RUN_LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("another supervised Orin run currently owns the campaign lock") from error
        try:
            verify_model_checksums()
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def workload_path(suite, workload):
    root = HERE if suite == "screen" else HERE / "confirmation"
    return root / workload_filename(workload)


def config_path(variant):
    if variant == "baseline":
        return HERE / "config-mtp-off.json"
    if variant == "candidate":
        return HERE / "config-mtp3.json"
    raise ValueError(f"unknown campaign variant: {variant}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("screen", "confirm"), required=True)
    parser.add_argument("--campaign-name", required=True,
                        help="new output directory under this experiment")
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--plan-only", action="store_true",
                        help="print schedule and identities without starting services")
    args = parser.parse_args()
    campaign_name = Path(args.campaign_name)
    if campaign_name.is_absolute() or ".." in campaign_name.parts:
        raise ValueError("campaign name must stay below this experiment directory")
    repetitions = 3 if args.suite == "screen" else 7
    schedule = make_schedule(repetitions, args.seed)
    configs = {variant: json.loads(config_path(variant).read_text())
               for variant in ("baseline", "candidate")}
    binary_sha = verify_config_pair(configs)
    workloads = {name: workload_path(args.suite, name) for name in ("short", "near_limit")}
    if any(not path.is_file() for path in workloads.values()):
        raise FileNotFoundError(f"missing {args.suite} workloads; prepare them before running")
    campaign_root = HERE / campaign_name
    if args.plan_only:
        print(json.dumps({"suite": args.suite, "seed": args.seed,
                          "repetitions_per_workload": repetitions,
                          "binary_sha256": binary_sha,
                          "workload_sha256": {name: sha256(path) for name, path in workloads.items()},
                          "schedule": schedule}, indent=2))
        return 0
    if campaign_root.exists():
        raise FileExistsError(f"refusing to overwrite {campaign_root}")
    verify_artifacts_while_idle()
    campaign_root.mkdir()
    launch_root = campaign_root / "launch-logs"
    launch_root.mkdir()
    campaign = {
        "schema": 1,
        "scope": f"Q2_0 int8-KV MTP × workload {args.suite}",
        "suite": args.suite,
        "seed": args.seed,
        "repetitions_per_workload": repetitions,
        "planned_blocks": len(schedule) // 2,
        "schedule": schedule,
        "binary_source_commit": SOURCE_COMMIT,
        "binary_sha256": binary_sha,
        "config_sha256": {name: sha256(config_path(name))
                          for name in ("baseline", "candidate")},
        "model_checksums_file_sha256": sha256(HERE / "model-checksums.txt"),
        "model_checksums": [line for line in (HERE / "model-checksums.txt").read_text().splitlines()
                            if line.strip() and not line.lstrip().startswith("#")],
        "workload_sha256": {name: sha256(path) for name, path in workloads.items()},
        "started_wall_time": time.time(),
        "status": "running",
        "runs": [],
    }
    campaign_path = campaign_root / "campaign.json"

    def save():
        temporary = campaign_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(campaign, indent=2) + "\n")
        temporary.replace(campaign_path)

    save()
    try:
        for item in schedule:
            require_campaign_lock_free()
            if sha256(Path(configs["baseline"]["exe"])) != binary_sha:
                raise RuntimeError("candidate binary changed during the campaign")
            variant = item["variant"]
            block = item["block"]
            output = campaign_root / f"block-{block:02d}-{variant}"
            command = [
                "systemd-run", "--user", "--scope", "--collect",
                "-p", "MemoryMax=28G", "-p", "IOAccounting=yes",
                sys.executable, str(ROOT / "tools/integration/run_control.py"),
                "--output", str(output), "--timeout", "1800", "--interval", "1",
                "--sample-clocks", "--", sys.executable,
                str(ROOT / "tools/integration/api_control_block.py"),
                "--config", str(config_path(variant)),
                "--workloads", str(workloads[item["workload"]]),
                "--output", str(output / "requests.json"), "--variant", variant,
                "--warmup-workloads", str(HERE / "warmup-workloads.json"), "--no-trace",
            ]
            run = {**item, "status": "running", "started_wall_time": time.time(),
                   "output_dir": output.relative_to(ROOT).as_posix(), "command": command}
            campaign["runs"].append(run)
            save()
            with (launch_root / f"block-{block:02d}-{variant}.txt").open("w") as log:
                completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            result_path = output / "result.json"
            if result_path.is_file():
                supervised = json.loads(result_path.read_text())
                run["supervisor_status"] = supervised.get("status")
                run["supervisor_returncode"] = supervised.get("returncode")
            run["returncode"] = completed.returncode
            run["finished_wall_time"] = time.time()
            run["binary_sha256_after"] = sha256(Path(configs["baseline"]["exe"]))
            run["status"] = ("pass" if completed.returncode == 0
                              and run["binary_sha256_after"] == binary_sha else "fail")
            save()
            print(f"{item['workload']} block={block} variant={variant} status={run['status']}",
                  flush=True)
            if run["status"] != "pass":
                campaign["abort_reason"] = f"stopped after failed arm: {run['output_dir']}"
                break
    except BaseException as error:
        campaign["status"] = "interrupted"
        campaign["abort_reason"] = f"{type(error).__name__}: {error}"
        campaign["finished_wall_time"] = time.time()
        save()
        raise
    campaign["finished_wall_time"] = time.time()
    campaign["status"] = "pass" if all(run["status"] == "pass" for run in campaign["runs"]) else "fail"
    save()
    return 0 if campaign["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
