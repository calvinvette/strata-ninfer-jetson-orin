#!/usr/bin/env python3
"""Compare serial and two-slot streamed API retrieval on distinct Q2_0 prompts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from benchmark_control import request, stream_request  # noqa: E402


def check_port(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))


def wait_health(base, server):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"server exited before readiness: {server.returncode}")
        try:
            health = request(base, "/health", timeout=5)
            if health.get("model"):
                return health
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(0.5)
    raise TimeoutError("server readiness deadline")


def stream_one(base, model, workload):
    body = {"model": model, "messages": workload["messages"], "temperature": 0,
            "max_tokens": workload["generate_tokens"],
            "chat_template_kwargs": {"enable_thinking": False}}
    start = time.monotonic()
    response, observed = stream_request(base, body)
    end = time.monotonic()
    usage = response.get("usage", {})
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    timings = response.get("timings", {})
    codes = workload.get("expected_codes", [])
    positions = [content.find(code) for code in codes]
    quality = (usage.get("prompt_tokens") == workload["prompt_tokens"]
               and usage.get("completion_tokens", 0) > 0
               and all(content.count(code) == 1 for code in codes)
               and all(pos >= 0 for pos in positions) and positions == sorted(positions))
    return {"cell": workload["cell"], "start_monotonic_s": start,
            "end_monotonic_s": end, "elapsed_s": end - start,
            "ttft_s": observed.get("first_visible_delta_s"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cached_prompt_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "timings": timings, "expected_codes": codes,
            "code_positions": positions, "quality_pass": quality,
            "content": content}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--workload-8k", type=Path, required=True)
    ap.add_argument("--workload-16k", type=Path, required=True)
    ap.add_argument("--warmup", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    base_config = json.loads(args.config.read_text())
    workloads = [json.loads(p.read_text())["workloads"][0]
                 for p in (args.workload_8k, args.workload_16k)]
    warmup = json.loads(args.warmup.read_text())["workloads"][0]
    result = {"status": "not_run", "binary_sha256": hashlib.sha256(
        Path(base_config["exe"]).read_bytes()).hexdigest(),
        "base_config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "workload_sha256": [hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (args.workload_8k, args.workload_16k)],
            "serial": {}, "parallel2": {}, "max_running_observed": 0,
            "max_active_slots_observed": 0}
    output_path = args.output / "result.json"

    def save():
        output_path.write_text(json.dumps(result, indent=2) + "\n")

    def run_arm(name, parallel):
        arm_dir = args.output / name
        arm_dir.mkdir()
        cfg = dict(base_config)
        cfg["args"] = list(base_config["args"])
        cfg["env"] = dict(base_config.get("env", {}))
        for key in ("STRATA_TRACE", "STRATA_STATE_HASH", "STRATA_STATE_HASH_GDN",
                    "STRATA_INTEGRATION_TRACE", "STRATA_ACCEPTED_PREFIX_TRACE"):
            cfg["env"].pop(key, None)
        cfg["log"] = str((arm_dir / "engine.log").resolve())
        cfg["model_name"] = f"Q2_0 16K-context API concurrency {name}"
        cfg.pop("parallel", None)
        if parallel:
            cfg["parallel"] = 2
        owned = arm_dir / "server-config.json"
        owned.write_text(json.dumps(cfg, indent=2) + "\n")
        port = int(cfg["port"])
        check_port(port)
        base = f"http://127.0.0.1:{port}"
        server = subprocess.Popen([sys.executable, "-m", "serve.server", "--engine", "strata",
                                   "--config", str(owned.resolve()), "--host", "127.0.0.1",
                                   "--port", str(port)], cwd=cfg["cwd"],
                                  env=os.environ | cfg["env"])
        try:
            health = wait_health(base, server)
            arm = {"health": health, "warmup": None, "requests": []}
            arm["warmup"] = stream_one(base, health["model"], warmup)
            if parallel:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(stream_one, base, health["model"], w)
                               for w in workloads]
                    while not all(f.done() for f in futures):
                        try:
                            metrics = request(base, "/metrics", timeout=5)
                            live = metrics.get("live", {})
                            active = sum(slot.get("state") != "idle"
                                         for slot in live.get("slots", []))
                            result["max_running_observed"] = max(
                                result["max_running_observed"], int(live.get("running", 0)))
                            result["max_active_slots_observed"] = max(
                                result["max_active_slots_observed"], active)
                        except (urllib.error.URLError, OSError, ValueError):
                            pass
                        time.sleep(0.5)
                    arm["requests"] = [f.result() for f in futures]
            else:
                for workload in workloads:
                    arm["requests"].append(stream_one(base, health["model"], workload))
            arm["batch_slots_reported"] = request(base, "/v1/status", timeout=10).get(
                "concurrency", {}).get("serving")
            return arm
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)

    try:
        result["serial"] = run_arm("serial", False)
        save()
        result["parallel2"] = run_arm("parallel2", True)
        serial_rows = result["serial"]["requests"]
        parallel_rows = result["parallel2"]["requests"]
        result["serial_quality"] = all(r["quality_pass"] for r in serial_rows)
        result["parallel_quality"] = all(r["quality_pass"] for r in parallel_rows)
        result["parallel_slots_admitted"] = result["parallel2"]["batch_slots_reported"] == 2
        result["overlap_observed"] = (result["max_running_observed"] >= 2
                                       and result["max_active_slots_observed"] >= 2)
        result["status"] = "pass" if all((result["serial_quality"],
                                            result["parallel_quality"],
                                            result["parallel_slots_admitted"],
                                            result["overlap_observed"])) else "fail"
        result["reason"] = ("serial and overlapping two-slot streamed requests passed independent retrieval checks"
                            if result["status"] == "pass" else "quality, slot admission, or overlap check failed")
        return 0 if result["status"] == "pass" else 1
    except Exception as exc:
        result["status"] = "fail"
        result["reason"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        save()


if __name__ == "__main__":
    raise SystemExit(main())
