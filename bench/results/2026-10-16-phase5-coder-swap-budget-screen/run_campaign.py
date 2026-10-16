#!/usr/bin/env python3
"""Execute and retain the randomized, supervised swap-budget screen."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from prepare_campaign import make_schedule

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOCK = Path("/tmp") / f"strata-integration-campaign-{os.getuid()}.lock"
EXPECTED_BINARY = "fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b"
EXPECTED_MODEL_SHARDS = {
    "Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf":
        "e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad",
    "Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf":
        "316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(out)
    config = json.loads((ROOT / "bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/baseline-mtp0-config.json").read_text())
    binary = Path(config["exe"])
    actual_binary = sha256(binary)
    if actual_binary != EXPECTED_BINARY:
        raise RuntimeError(f"unexpected service binary hash: {actual_binary}")
    native = Path(config["args"][config["args"].index("--native") + 1])
    ple = Path(config["args"][config["args"].index("--ple-gguf") + 1])
    model_shards = {native.name: sha256(native), ple.name: sha256(ple)}
    if model_shards != EXPECTED_MODEL_SHARDS:
        raise RuntimeError(f"unexpected Coder IQ1_M shard hashes: {model_shards}")
    schedule = make_schedule(args.seed)
    if args.plan_only:
        print(json.dumps({"seed": args.seed, "binary_sha256": actual_binary,
                          "schedule": schedule}, indent=2))
        return 0
    out.mkdir(parents=True)
    campaign = {"schema": 1, "scope": "Coder IQ1_M adaptive swap-budget × recovery stability",
                "seed": args.seed, "binary_sha256": actual_binary,
                "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
                "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
                "model_quantization": "IQ1_M", "model_shard_sha256": model_shards,
                "source_commit": "e6a55b30f596ecc5173d2eb55a4087662b7ee88f",
                "blocks": 3, "schedule": schedule, "status": "running", "runs": []}
    path = out / "campaign.json"

    def save():
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(campaign, indent=2) + "\n")
        temp.replace(path)

    save()
    with LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("another supervised Orin campaign owns the device") from error
        for item in schedule:
            run = {**item, "status": "running", "started_wall_time": time.time()}
            campaign["runs"].append(run)
            save()
            run_dir = out / f"block-{item['block']}-{item['name']}"
            supervisor_dir = out / f"block-{item['block']}-{item['name']}-supervisor"
            cmd = ["systemd-run", "--user", "--scope", "--collect",
                   "-p", "MemoryMax=28G", "-p", "IOAccounting=yes",
                   sys.executable, str(ROOT / "tools/integration/run_control.py"),
                   "--output", str(supervisor_dir), "--timeout", "1800",
                   "--interval", "1", "--sample-clocks", "--", sys.executable,
                   str(HERE / "run_one.py"), "--adapt-every", str(item["adapt_every"]),
                   "--adapt-swaps", str(item["adapt_swaps"]), "--output", str(run_dir)]
            run["command"] = cmd
            try:
                completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            except BaseException:
                run["status"] = "interrupted"
                run["finished_wall_time"] = time.time()
                save()
                raise
            (run_dir.parent / f"{run_dir.name}.launch.txt").write_text(
                completed.stdout + completed.stderr)
            supervised = supervisor_dir / "result.json"
            supervisor_status = json.loads(supervised.read_text()).get("status") if supervised.exists() else None
            result = run_dir / "analysis.json"
            valid = result.exists() and json.loads(result.read_text()).get("binary_sha256") == actual_binary
            run.update({"returncode": completed.returncode, "supervisor_status": supervisor_status,
                        "status": "pass" if completed.returncode == 0 and supervisor_status == "pass" and valid else "fail",
                        "finished_wall_time": time.time(), "binary_sha256_after": sha256(binary)})
            save()
            print(f"block={item['block']} arm={item['name']} status={run['status']}", flush=True)
            if run["status"] != "pass":
                campaign["abort_reason"] = f"stopped at {run_dir.name}"
                break
        fcntl.flock(lock, fcntl.LOCK_UN)
    campaign["finished_wall_time"] = time.time()
    campaign["status"] = "pass" if len(campaign["runs"]) == len(schedule) and all(
        run["status"] == "pass" for run in campaign["runs"]) else "fail"
    save()
    return 0 if campaign["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
