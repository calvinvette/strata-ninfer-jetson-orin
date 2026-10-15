#!/usr/bin/env python3
"""Exercise four distinct 8K retrieval streams in separate Strata batch slots."""
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


def stream_one(base, model, workload):
    body = {"model": model, "messages": workload["messages"], "temperature": 0,
            "max_tokens": workload["generate_tokens"],
            "chat_template_kwargs": {"enable_thinking": False}}
    start = time.monotonic()
    response, observed = stream_request(base, body)
    end = time.monotonic()
    usage = response.get("usage", {})
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    codes = workload.get("expected_codes", [])
    positions = [content.find(code) for code in codes]
    passed = (usage.get("prompt_tokens") == workload["prompt_tokens"]
              and usage.get("completion_tokens", 0) > 0
              and all(content.count(code) == 1 for code in codes)
              and all(x >= 0 for x in positions)
              and positions == sorted(positions))
    return {"cell": workload["cell"], "elapsed_s": end-start,
            "ttft_s": observed.get("first_visible_delta_s"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cached_prompt_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "expected_codes": codes, "positions": positions,
            "quality_pass": passed, "content": content}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--warmup", type=Path, required=True)
    ap.add_argument("--workloads", nargs=4, type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    workloads = [json.loads(p.read_text())["workloads"][0] for p in args.workloads]
    warmup = json.loads(args.warmup.read_text())["workloads"][0]
    port = int(cfg["port"])
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
    cfg["log"] = str((args.output / "engine.log").resolve())
    owned = args.output / "server-config.json"
    owned.write_text(json.dumps(cfg, indent=2) + "\n")
    base = f"http://127.0.0.1:{port}"
    result = {"status": "not_run", "binary_sha256": hashlib.sha256(Path(cfg["exe"]).read_bytes()).hexdigest(),
              "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
              "workload_sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in args.workloads],
              "max_running_observed": 0, "max_active_slots_observed": 0, "requests": []}
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    server = subprocess.Popen([sys.executable, "-m", "serve.server", "--engine", "strata",
                              "--config", str(owned.resolve()), "--host", "127.0.0.1",
                              "--port", str(port)], cwd=cfg["cwd"], env=os.environ | cfg.get("env", {}))
    try:
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"server exited during startup: {server.returncode}")
            try:
                health = request(base, "/health", timeout=5)
                if health.get("model"):
                    break
            except (urllib.error.URLError, OSError, ValueError):
                time.sleep(0.5)
        else:
            raise TimeoutError("server readiness deadline")
        result["health"] = health
        result["warmup"] = stream_one(base, health["model"], warmup)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(stream_one, base, health["model"], w) for w in workloads]
            while not all(f.done() for f in futures):
                try:
                    live = request(base, "/metrics", timeout=5).get("live", {})
                    active = sum(slot.get("state") != "idle" for slot in live.get("slots", []))
                    result["max_running_observed"] = max(result["max_running_observed"], int(live.get("running", 0)))
                    result["max_active_slots_observed"] = max(result["max_active_slots_observed"], active)
                except (urllib.error.URLError, OSError, ValueError):
                    pass
                time.sleep(0.5)
            result["requests"] = [f.result() for f in futures]
        result["batch_slots_reported"] = request(base, "/v1/status", timeout=10).get("concurrency", {}).get("serving")
        result["quality_pass"] = len(result["requests"]) == 4 and all(x["quality_pass"] for x in result["requests"])
        result["all_slots_admitted"] = result["batch_slots_reported"] == 4
        result["overlap_observed"] = result["max_running_observed"] >= 4 and result["max_active_slots_observed"] >= 4
        result["status"] = "pass" if all(result[k] for k in ("quality_pass", "all_slots_admitted", "overlap_observed")) else "fail"
        result["reason"] = "four distinct retrieval requests overlapped in four slots and passed their oracles" if result["status"] == "pass" else "quality, admission, or overlap check failed"
        return 0 if result["status"] == "pass" else 1
    except Exception as exc:
        result["status"] = "fail"
        result["reason"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
