#!/usr/bin/env python3
"""Sustain serial streaming requests for one fixed loopback Strata workload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "integration")]
from benchmark_control import request, stream_request


def check_port(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))


def wait_health(base, server):
    deadline = time.monotonic() + 240
    while True:
        if server.poll() is not None:
            raise RuntimeError(f"server exited before readiness: {server.returncode}")
        try:
            health = request(base, "/health", timeout=5)
            if health.get("model"):
                return health
        except (urllib.error.URLError, OSError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError("server readiness deadline")
        time.sleep(0.5)


def call(base, model, messages, max_tokens, expected_prompt=None):
    body = {"model": model, "messages": messages, "temperature": 0,
            "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": False}}
    started = time.monotonic()
    response, observation = stream_request(base, body)
    end = time.monotonic()
    usage = response.get("usage", {})
    timings = response.get("timings", {})
    if expected_prompt is not None and usage.get("prompt_tokens") != expected_prompt:
        raise RuntimeError(f"prompt token mismatch: {usage.get('prompt_tokens')} != {expected_prompt}")
    if usage.get("completion_tokens", 0) <= 0 or not timings:
        raise RuntimeError("missing completion tokens or engine timings")
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"start_monotonic_s": started, "end_monotonic_s": end,
            "elapsed_s": end - started,
            "ttft_s": observation.get("first_visible_delta_s"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cached_prompt_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "timings": timings, "content": content}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--workload", type=Path, required=True)
    ap.add_argument("--warmup-workload", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--duration-seconds", type=int, default=2400,
                    help="sustained interval after a cold full-prompt retrieval run")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    workload = json.loads(args.workload.read_text())["workloads"][0]
    warmup = json.loads(args.warmup_workload.read_text())["workloads"][0]
    expected = workload["expected_codes"]
    base = f"http://127.0.0.1:{cfg['port']}"
    check_port(cfg["port"])
    cfg["log"] = str((args.output / "engine.log").resolve())
    cfg["env"] = dict(cfg.get("env", {}))
    for key in ("STRATA_TRACE", "STRATA_STATE_HASH", "STRATA_STATE_HASH_GDN",
                "STRATA_INTEGRATION_TRACE", "STRATA_ACCEPTED_PREFIX_TRACE"):
        cfg["env"].pop(key, None)
    owned_config = args.output / "server-config.json"
    owned_config.write_text(json.dumps(cfg, indent=2) + "\n")
    server = subprocess.Popen([sys.executable, "-m", "serve.server", "--engine", "strata",
                               "--config", str(owned_config.resolve()), "--host", "127.0.0.1",
                               "--port", str(cfg["port"])], cwd=cfg["cwd"], env=os.environ | cfg["env"])
    result_path = args.output / "result.json"
    requests_path = args.output / "requests.jsonl"
    summary = {
        "status": "not_run",
        "requested_duration_s": args.duration_seconds,
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "workload_sha256": hashlib.sha256(args.workload.read_bytes()).hexdigest(),
        "engine_sha256": hashlib.sha256(Path(cfg["exe"]).read_bytes()).hexdigest(),
        "expected_codes": expected,
        "precondition": {},
        "started_wall_time": time.time(),
    }
    request_count = 0
    failures = 0
    try:
        health = wait_health(base, server)
        summary["health"] = health
        summary["capabilities"] = request(base, "/metrics", timeout=5)
        warm = call(base, health["model"], warmup["messages"], warmup["generate_tokens"],
                    warmup["prompt_tokens"])
        summary["warmup"] = {k: v for k, v in warm.items() if k != "content"}
        first = call(base, health["model"], workload["messages"], workload["generate_tokens"],
                     workload["prompt_tokens"])
        if not all(first["content"].count(code) == 1 for code in expected):
            raise RuntimeError("precondition retrieval did not contain each code exactly once")
        first["quality_pass"] = True
        summary["precondition"] = {k: v for k, v in first.items() if k != "content"}
        loop_start = time.monotonic()
        summary["loop_start_monotonic_s"] = loop_start
        deadline = loop_start + args.duration_seconds
        with requests_path.open("w", encoding="utf-8") as out:
            while time.monotonic() < deadline:
                try:
                    row = call(base, health["model"], workload["messages"],
                               workload["generate_tokens"], workload["prompt_tokens"])
                    row["request_index"] = request_count
                    row["quality_pass"] = all(row["content"].count(code) == 1 for code in expected)
                    row["cache_reuse"] = row["cached_prompt_tokens"] > 0 or row["timings"].get("cache_n", 0) > 0
                    if not row["quality_pass"]:
                        failures += 1
                    out.write(json.dumps(row, separators=(",", ":")) + "\n")
                    out.flush()
                except Exception as exc:
                    failures += 1
                    row = {"request_index": request_count, "error": f"{type(exc).__name__}: {exc}",
                           "end_monotonic_s": time.monotonic(), "quality_pass": False}
                    out.write(json.dumps(row, separators=(",", ":")) + "\n")
                    out.flush()
                request_count += 1
        summary["loop_end_monotonic_s"] = time.monotonic()
        summary["measured_duration_s"] = summary["loop_end_monotonic_s"] - loop_start
        summary["request_count"] = request_count
        summary["failed_or_wrong_requests"] = failures
        summary["status"] = "pass" if summary["measured_duration_s"] >= args.duration_seconds and failures == 0 else "fail"
        summary["reason"] = "duration, streaming completion, and retrieval criteria passed" if summary["status"] == "pass" else "duration shortfall or failed retrieval/request"
        return 0 if summary["status"] == "pass" else 1
    except Exception as exc:
        summary["status"] = "fail"
        summary["reason"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        summary["request_count"] = request_count
        summary["failed_or_wrong_requests"] = failures
        summary["finished_wall_time"] = time.time()
        result_path.write_text(json.dumps(summary, indent=2) + "\n")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
