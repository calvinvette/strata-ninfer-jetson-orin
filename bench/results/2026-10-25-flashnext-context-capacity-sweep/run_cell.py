#!/usr/bin/env python3
"""Run one exact Oct-8-style context-capacity cell on the current Orin port."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

import requests


ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = {
    "coder-iq1m": ROOT / "bench/results/2026-10-24-coder-iq1m-current-candidate-performance/server-config.template.json",
    "coder-q2_0": ROOT / "bench/results/2026-10-25-q2-current-candidate-performance/server-config.template.json",
    "original-iq3_s": ROOT / "bench/results/2026-10-24-iq3s-current-candidate-performance/server-config.template.json",
}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def api_json(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def make_request(base, model, repeat, round_index, output):
    prompt = (f"Experiment {round_index}, size {repeat}. Context: " +
              "red green blue yellow " * repeat +
              "\nWrite at least 200 words explaining how a computer processes information. Start with the processor.")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 64,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": True,
    }
    start = time.monotonic()
    req = requests.post(base + "/v1/chat/completions", json=body, stream=True, timeout=(15, 21600))
    req.raise_for_status()
    first_visible = None
    text = []
    final = {}
    try:
        for line in req.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            payload = line[6:].strip()
            if payload == b"[DONE]":
                break
            chunk = json.loads(payload)
            elapsed = time.monotonic() - start
            if chunk.get("usage"):
                final.update(chunk)
            if chunk.get("timings"):
                final["timings"] = chunk["timings"]
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                piece = delta.get("content") or delta.get("reasoning_content") or ""
                if piece:
                    if first_visible is None:
                        first_visible = elapsed
                    text.append(piece)
    finally:
        req.close()
    elapsed = time.monotonic() - start
    content = "".join(text)
    usage = final.get("usage", {})
    timings = final.get("timings", {})
    row = {
        "repeat": repeat,
        "round": round_index,
        "expected_prompt_tokens_reference": {32: 172, 128: 557, 256: 1069}[repeat],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cached_prompt_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens"),
        "client_ttft_s": first_visible,
        "client_total_s": elapsed,
        "prompt_ms": timings.get("prompt_ms"),
        "prompt_tok_s": timings.get("prompt_per_second"),
        "decode_ms": timings.get("predicted_ms"),
        "decode_tok_s": timings.get("predicted_per_second"),
        "draft_tokens": timings.get("draft_n"),
        "accepted_draft_tokens": timings.get("draft_n_accepted"),
        "output_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "output_text": content,
        "status": "pass",
    }
    expected_tokens = row["expected_prompt_tokens_reference"]
    # Chat template token counts are checked against the October 8 reference
    # corpus. Differences are preserved as invalid/changed-input cells.
    if row["prompt_tokens"] != expected_tokens:
        row.update(status="invalid_prompt_token_count", reason="formatted token count differs from reference corpus")
    elif row["completion_tokens"] != 64:
        row.update(status="invalid_output_count", reason="request did not generate exactly 64 tokens")
    elif row["cached_prompt_tokens"] not in (0, None):
        row.update(status="invalid_prefix_reuse", reason="matched request reused cached prompt tokens")
    elif not timings or not row["prompt_tok_s"] or not row["decode_tok_s"] or first_visible is None:
        row.update(status="invalid_missing_metric", reason="missing engine timing or client TTFT")
    save(output, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=sorted(TEMPLATES), required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18887)
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = json.loads(TEMPLATES[args.model].read_text())
    args_list = config["args"]
    context_index = args_list.index("--max-context") + 1
    args_list[context_index] = str(args.context)
    config["model_name"] = f"Flash-Next context sweep {args.model} ctx{args.context}"
    config["log"] = str((output / "engine.log").resolve())
    config["port"] = args.port
    config_path = output / "server-config.json"
    save(config_path, config)
    base = f"http://127.0.0.1:{args.port}"
    result = {
        "model": args.model,
        "context_capacity": args.context,
        "binary_sha256": hashlib.file_digest(Path(config["exe"]).open("rb"), "sha256").hexdigest(),
        "server_config": str(config_path),
        "status": "starting",
        "requests": [],
        "protocol": "Oct-8 matched-prompt sweep (3 rounds x repeat counts 32/128/256; max_tokens=64; no separate warmup); streaming added to observe client TTFT",
    }
    save(output / "cell.json", result)
    server_env = os.environ.copy()
    server_env.update({str(k): str(v) for k, v in config.get("env", {}).items()})
    server_log = (output / "server.txt").open("w")
    server = subprocess.Popen(
        [sys.executable, "-m", "serve.server", "--engine", "strata", "--config", str(config_path),
         "--host", "127.0.0.1", "--port", str(args.port)],
        cwd=config["cwd"], env=server_env, stdout=server_log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 900
        health = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"server exited before readiness: {server.returncode}")
            try:
                health = api_json(base + "/health", timeout=5)
                if health.get("loaded") and health.get("model") == config["model_name"]:
                    break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError("server readiness deadline")
        result["health"] = health
        result["status"] = "running"
        save(output / "cell.json", result)
        for round_index in range(3):
            for repeat in (32, 128, 256):
                expected_prompt = {32: 172, 128: 557, 256: 1069}[repeat]
                if expected_prompt + 64 > args.context:
                    continue
                row_path = output / f"matched-{round_index}-{repeat}.json"
                print(f"{args.model} ctx={args.context} repeat={repeat} round={round_index}", flush=True)
                row = make_request(base, config["model_name"], repeat, round_index, row_path)
                result["requests"].append(str(row_path))
                save(output / "cell.json", result)
                if row["status"] != "pass":
                    raise RuntimeError(row.get("reason", row["status"]))
        result["status"] = "passed"
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if server.poll() is None:
            os.killpg(server.pid, signal.SIGINT)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait()
        server_log.close()
        save(output / "cell.json", result)
    print(json.dumps({k: result[k] for k in ("model", "context_capacity", "status", "error") if k in result}, indent=2))


if __name__ == "__main__":
    main()
