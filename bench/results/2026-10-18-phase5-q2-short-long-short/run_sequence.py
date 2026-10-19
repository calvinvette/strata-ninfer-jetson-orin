#!/usr/bin/env python3
"""Check same-service short/long/short output stability on a fixed Q2_0 profile."""
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
from benchmark_control import request, stream_request


def load_case(path):
    return json.loads(path.read_text())["workloads"][0]


def check_port(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))


def wait_health(base, server):
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"server exited before readiness: {server.returncode}")
        try:
            health = request(base, "/health", timeout=5)
            if health.get("model"):
                return health
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    raise TimeoutError("server readiness deadline")


def call(base, model, case):
    body = {"model": model, "messages": case["messages"], "temperature": 0,
            "max_tokens": case["generate_tokens"],
            "chat_template_kwargs": {"enable_thinking": False}}
    start = time.monotonic()
    response, observation = stream_request(base, body)
    elapsed = time.monotonic() - start
    usage = response.get("usage", {})
    timings = response.get("timings", {})
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    if usage.get("prompt_tokens") != case["prompt_tokens"]:
        raise RuntimeError(f"prompt token mismatch: {usage.get('prompt_tokens')} != {case['prompt_tokens']}")
    if usage.get("completion_tokens", 0) <= 0 or not timings:
        raise RuntimeError("missing completion tokens or engine timings")
    return {"elapsed_s": elapsed, "ttft_s": observation.get("first_visible_delta_s"),
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cached_prompt_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "timings": timings, "content": content}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--short-workload", type=Path, required=True)
    ap.add_argument("--long-workload", type=Path, required=True)
    ap.add_argument("--warmup-workload", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    short = load_case(args.short_workload)
    long = load_case(args.long_workload)
    warmup = load_case(args.warmup_workload)
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
        "short_workload_sha256": hashlib.sha256(args.short_workload.read_bytes()).hexdigest(),
        "long_workload_sha256": hashlib.sha256(args.long_workload.read_bytes()).hexdigest(),
        "warmup_sha256": hashlib.sha256(args.warmup_workload.read_bytes()).hexdigest(),
        "engine_sha256": hashlib.sha256(Path(cfg["exe"]).read_bytes()).hexdigest(),
    }
    server = subprocess.Popen([sys.executable, "-m", "serve.server", "--engine", "strata",
                               "--config", str(config_path.resolve()), "--host", "127.0.0.1",
                               "--port", str(cfg["port"])], cwd=cfg["cwd"],
                              env=os.environ | cfg["env"])
    try:
        health = wait_health(base, server)
        result["health"] = health
        result["capabilities"] = request(base, "/metrics", timeout=5)
        result["warmup"] = call(base, health["model"], warmup)
        result["short_before"] = call(base, health["model"], short)
        result["long"] = call(base, health["model"], long)
        result["short_after"] = call(base, health["model"], short)

        short_codes = short["expected_codes"]
        expected_short = (f"EARLY={short_codes[0]}, MIDDLE={short_codes[1]}, "
                          f"LATE={short_codes[2]}, SUM={short['expected_suffix_sum']}")
        codes = long["expected_codes"]
        long_answer = result["long"]["content"]
        positions = [long_answer.find(code) for code in codes]
        result["checks"] = {
            "short_prompt_uncached": all(result[key]["cached_prompt_tokens"] == 0 and
                                          result[key]["timings"].get("cache_n", 0) == 0
                                          for key in ("short_before", "short_after")),
            "short_output_exactly_stable": result["short_before"]["content"].strip() ==
                result["short_after"]["content"].strip(),
            "short_answers_match_independent_oracle": all(
                result[key]["content"].strip() == expected_short
                for key in ("short_before", "short_after")),
            "long_markers_once_and_ordered": all(long_answer.count(code) == 1 for code in codes)
                and all(pos >= 0 for pos in positions)
                and positions == sorted(positions),
        }
        result["checks"]["all_pass"] = all(result["checks"].values())
        result["status"] = "pass" if result["checks"]["all_pass"] else "fail"
        result["reason"] = ("same-service uncached short answer matched across long retrieval; "
                            "long markers passed" if result["status"] == "pass" else
                            "one or more output, cache or retrieval checks failed")
        return 0 if result["status"] == "pass" else 1
    except Exception as exc:
        result["status"] = "fail"
        result["reason"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
