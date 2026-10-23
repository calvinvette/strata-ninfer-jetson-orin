#!/usr/bin/env python3
"""Three-block, paired timing screen for the Coder expert-233 profile."""
import argparse
import json
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, remove_arg, replace_arg


def elapsed_generate(engine, prompt, token_limit):
    start = time.perf_counter()
    tokens = [int(t) for t in engine.generate(prompt, token_limit, {"temperature": 0}, threading.Event())
              if t is not None]
    return {"tokens": tokens, "elapsed_s": time.perf_counter() - start}


def run_arm(cfg, prompts, profile_path, tokens, output):
    args = list(cfg["args"])
    for key in ("--mtp", "--mtp-max-t", "--adapt-every", "--adapt-accepted-only"):
        remove_arg(args, key)
    replace_arg(args, "--spec", "2")
    replace_arg(args, "--max-context", "1024")
    replace_arg(args, "--expert-cache", "1500")
    replace_arg(args, "--prompt-cache", "6")
    replace_arg(args, "--expert-profile", str(profile_path.resolve()))
    env = child_env(cfg)
    env.update({"STRATA_NATIVE_CPU_Q8_1_DOT": "all", "STRATA_IQ_MT_MIN": "1",
                "STRATA_PREFILL_CPU_SHARE": "0"})
    for key in ("STRATA_INTEGRATION_TRACE", "STRATA_STATE_HASH", "STRATA_ACCEPTED_PREFIX_TRACE",
                "STRATA_STATE_HASH_GDN", "STRATA_STATE_HASH_QSA_LAYERS",
                "STRATA_BATCH_GDN_HASH_PATH", "STRATA_VERIFY_DUMP_GDN_COMMIT_PATH",
                "STRATA_VERIFY_DUMP_GDN_PATH", "STRATA_VERIFY_DUMP_MOE_PARTS_PATH",
                "STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH", "STRATA_VERIFY_DUMP_MOE_ROUTE_PATH",
                "STRATA_CAPTURE_MOE_PATH"):
        env.pop(key, None)

    # Warm a disposable batch service so measured services see warm file pages
    # but no request state or prompt-cache entries from their own warmup.
    warmup = StrataEngine(cfg["exe"], args + ["--batch", "2"], cwd=cfg.get("cwd"),
                          log=str(output / "warmup.log"), env=env)
    try:
        if warmup.batch != 2:
            raise RuntimeError(f"warmup admitted {warmup.batch} slots, expected 2")
        with ThreadPoolExecutor(max_workers=2) as pool:
            warmups = {name: pool.submit(elapsed_generate, warmup, prompt, 2)
                       for name, prompt in prompts.items()}
            for future in warmups.values():
                future.result()
    finally:
        warmup.close()

    # Each serial control is a fresh process, matching the integration captures.
    serial_runs = {}
    for name, prompt in prompts.items():
        serial = StrataEngine(cfg["exe"], args, cwd=cfg.get("cwd"),
                              log=str(output / f"serial-{name}.log"), env=env)
        try:
            serial_runs[name] = elapsed_generate(serial, prompt, tokens)
        finally:
            serial.close()

    batch = StrataEngine(cfg["exe"], args + ["--batch", "2"], cwd=cfg.get("cwd"),
                         log=str(output / "batch.log"), env=env)
    try:
        if batch.batch != 2:
            raise RuntimeError(f"batch admitted {batch.batch} slots, expected 2")
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {name: pool.submit(elapsed_generate, batch, prompt, tokens)
                       for name, prompt in prompts.items()}
            batch_runs = {name: future.result() for name, future in futures.items()}
        batch_wall_s = time.perf_counter() - start
    finally:
        batch.close()

    return {"serial": serial_runs, "batch": batch_runs, "batch_wall_s": batch_wall_s,
            "batch_tokens_per_s": sum(len(x["tokens"]) for x in batch_runs.values()) / batch_wall_s,
            "token_parity": {name: serial_runs[name]["tokens"] == batch_runs[name]["tokens"]
                             for name in prompts}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--candidate-profile", type=Path, required=True)
    ap.add_argument("--tokens", type=int, default=96)
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--scope-memory-gib", type=int, default=28)
    a = ap.parse_args()
    if a.tokens < 1 or a.scope_memory_gib < 1:
        ap.error("tokens and memory scope must be positive")
    cfg = json.loads(a.config.read_text())
    prompts = prepared_prompts(cfg, 2)
    if a.output.exists():
        ap.error(f"output already exists: {a.output}")
    a.output.mkdir(parents=True)
    base = ROOT / "data/expert-profile-coder.bin"
    rng = random.Random(a.seed)
    block_order = list(range(1, 4))
    rng.shuffle(block_order)
    cells = []
    for block in block_order:
        arms = [("baseline", base), ("expert233_first", a.candidate_profile)]
        rng.shuffle(arms)
        cells.extend((block, arm, profile) for arm, profile in arms)
    campaign = {"seed": a.seed, "blocks": 3, "arms": ["baseline", "expert233_first"],
                "tokens_per_prompt": a.tokens, "warmup_tokens_per_prompt": 2,
                "requested_expert_cache_slots": 1500, "context_tokens": 1024,
                "mtp": False, "prompt_cache_slots": 6,
                "measurement": "parallel two-live batch wall time; per-request client elapsed time",
                "warmup": "disposable two-live engine process; timed batch starts fresh after model pages are warmed",
                "serial_controls": "one fresh engine per prompt, not included in batch metric",
                "clock_controls": "none; dynamic clocks sampled read-only by supervisor",
                "trace_hooks": False, "cells": []}
    (a.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")
    for order, (block, arm, profile) in enumerate(cells):
        cell = a.output / f"block-{block:02d}-{arm}"
        cell.mkdir()
        capture_path = cell / "arm.json"
        cmd = [sys.executable, str(Path(__file__).resolve()), "--_arm",
               str(a.config.resolve()), str(profile.resolve()), str(capture_path.resolve()),
               str(a.tokens)]
        # Run this module's private arm mode inside the same controlled supervisor used elsewhere.
        control = [sys.executable, str(ROOT / "tools/integration/run_control.py"),
                   "--output", str((cell / "supervisor").resolve()), "--timeout", str(a.timeout),
                   "--sample-clocks", "--", *cmd]
        if a.scope_memory_gib:
            control = ["systemd-run", "--user", "--scope", "--collect", "-p",
                       f"MemoryMax={a.scope_memory_gib}G", "-p", "IOAccounting=yes", *control]
        with (cell / "supervisor.txt").open("w") as log:
            code = subprocess.call(control, stdout=log, stderr=subprocess.STDOUT)
        status_path = cell / "supervisor" / "result.json"
        row = {"block": block, "arm": arm, "order": order, "profile_sha256": __import__("hashlib").sha256(profile.read_bytes()).hexdigest(),
               "supervisor_returncode": code, "status": "pass" if code == 0 and capture_path.exists() else "fail"}
        if status_path.exists():
            sup = json.loads(status_path.read_text())
            row.update({"supervisor_status": sup.get("status"),
                        "minimum_available_bytes": sup.get("minimum_available_bytes"),
                        "minimum_admission_available_bytes": sup.get("minimum_admission_available_bytes"),
                        "elapsed_s": sup.get("elapsed_s"), "reason": sup.get("reason")})
            if sup.get("status") != "pass":
                row["status"] = sup.get("status")
        if capture_path.exists():
            result = json.loads(capture_path.read_text())
            row["batch_wall_s"] = result["batch_wall_s"]
            row["batch_tokens_per_s"] = result["batch_tokens_per_s"]
            row["token_parity"] = result["token_parity"]
            row["request_elapsed_s"] = {k: v["elapsed_s"] for k, v in result["batch"].items()}
        campaign["cells"].append(row)
        (a.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")
        print(f"{order + 1}/{len(cells)} block {block} {arm}: {row['status']}", flush=True)
        if row["status"] != "pass":
            break
    if len(campaign["cells"]) != len(cells):
        campaign["unlaunched"] = [{"block": b, "arm": arm, "status": "not_run"}
                                  for b, arm, _ in cells[len(campaign["cells"]):]]
    (a.output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--_arm":
        _, _, config_path, profile_path, output_path, tokens = sys.argv
        config = json.loads(Path(config_path).read_text())
        Path(output_path).write_text(json.dumps(
            run_arm(config, prepared_prompts(config, 2), Path(profile_path), int(tokens),
                    Path(output_path).parent), indent=2) + "\n")
    else:
        main()
