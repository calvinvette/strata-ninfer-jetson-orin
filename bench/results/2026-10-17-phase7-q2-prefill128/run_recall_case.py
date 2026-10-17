#!/usr/bin/env python3
"""Own a loopback Strata service for one supervised long-context recall case."""
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

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "integration")]
from tools.integration.benchmark_control import request, stream_request


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


def stream_check(base, model, messages, expected_prompt_tokens=None, max_tokens=48):
    body = {"model": model, "messages": messages, "temperature": 0,
            "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": False}}
    start = time.monotonic()
    response, observation = stream_request(base, body)
    elapsed = time.monotonic() - start
    usage = response.get("usage", {})
    timings = response.get("timings", {})
    if expected_prompt_tokens is not None and usage.get("prompt_tokens") != expected_prompt_tokens:
        raise RuntimeError(f"formatted prompt count mismatch: {usage.get('prompt_tokens')} != {expected_prompt_tokens}")
    if usage.get("completion_tokens", 0) <= 0 or not timings:
        raise RuntimeError("request returned no completion tokens or engine timings")
    return {"elapsed_s": elapsed, "response": response, "stream_observation": observation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--warmup-workload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    workload = json.loads(args.workload.read_text())["workloads"][0]
    warmup = json.loads(args.warmup_workload.read_text())["workloads"][0]
    base = f"http://127.0.0.1:{cfg['port']}"
    check_port(cfg["port"])
    cfg["log"] = str((args.output / "engine.log").resolve())
    cfg["env"] = dict(cfg.get("env", {}))
    for key in ("STRATA_TRACE", "STRATA_STATE_HASH", "STRATA_STATE_HASH_GDN",
                "STRATA_INTEGRATION_TRACE", "STRATA_ACCEPTED_PREFIX_TRACE"):
        cfg["env"].pop(key, None)
    config_path = args.output / "server-config.json"
    config_path.write_text(json.dumps(cfg, indent=2) + "\n")
    result = {
        "status": "not_run",
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "workload_sha256": hashlib.sha256(args.workload.read_bytes()).hexdigest(),
        "engine_sha256": hashlib.sha256(Path(cfg["exe"]).read_bytes()).hexdigest(),
        "configured_context": next(int(cfg["args"][i + 1]) for i, x in enumerate(cfg["args"])
                                   if x == "--max-context"),
        "warmup": {}, "recall": {}, "recovery": {},
    }
    server = subprocess.Popen([sys.executable, "-m", "serve.server", "--engine", "strata",
                               "--config", str(config_path.resolve()), "--host", "127.0.0.1",
                               "--port", str(cfg["port"])], cwd=cfg["cwd"], env=os.environ | cfg["env"])
    try:
        health = wait_health(base, server)
        metrics = request(base, "/metrics", timeout=5)
        result["health"] = health
        result["capabilities"] = metrics
        if metrics.get("engine", {}).get("max_context") != result["configured_context"]:
            raise RuntimeError("server context does not match the tested reservation")
        result["warmup"] = stream_check(base, health["model"], warmup["messages"],
                                        warmup["prompt_tokens"], warmup["generate_tokens"])
        result["recall"] = stream_check(base, health["model"], workload["messages"],
                                        workload["prompt_tokens"], workload["generate_tokens"])
        answer = result["recall"]["response"]["choices"][0]["message"].get("content", "")
        codes = workload["expected_codes"]
        positions = [answer.find(code) for code in codes]
        result["answer"] = answer
        result["quality"] = {
            "expected_codes": codes,
            "positions": positions,
            "all_present_once": all(answer.count(code) == 1 for code in codes),
            "correct_order": all(a >= 0 and a < b for a, b in zip(positions, positions[1:])),
        }
        recovery = stream_check(base, health["model"],
                               [{"role": "user", "content": "Reply with exactly RECOVERED."}],
                               max_tokens=12)
        result["recovery"] = recovery
        recovery_text = recovery["response"]["choices"][0]["message"].get("content", "")
        result["recovery"]["expected_word_found"] = "RECOVERED" in recovery_text
        result["status"] = "pass" if (result["quality"]["all_present_once"] and
                                       result["quality"]["correct_order"] and
                                       result["recovery"]["expected_word_found"]) else "fail"
        result["reason"] = "all three retrieval markers and same-service recovery passed" if result["status"] == "pass" else "retrieval or same-service recovery criterion failed"
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return 0 if result["status"] == "pass" else 1
    except Exception as exc:
        result["status"] = "fail"
        result["reason"] = f"{type(exc).__name__}: {exc}"
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        raise
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
