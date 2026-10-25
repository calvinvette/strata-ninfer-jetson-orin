#!/usr/bin/env python3
"""Small randomized E2 service screen; not a performance confirmation campaign."""
import hashlib
import argparse
import http.client
import json
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = None
DEFAULT_OUT = Path(__file__).resolve().parent / "paired-screen"
ENGINE = ROOT / "build/integration/e0-cuda-build/strata"
MODEL = Path.home() / "models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf"
PLE = Path.home() / "models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf"
PACK = Path.home() / "models/strata-orin-validation/q2-ple-pack"
PROFILE = Path.home() / "models/strata-orin-validation/q2-expert-profile.bin"
TOKENIZER = Path.home() / "models/strata-orin-validation/pack/tokenizer"
PORT = 18894


def post_chat():
    body = json.dumps({
        "model": "strata-e2-q2",
        "messages": [{"role": "user", "content": "1+1"}],
        "max_tokens": 48,
        "temperature": 0,
        "stream": True,
    }).encode()
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=300)
    started = time.perf_counter()
    connection.request("POST", "/v1/chat/completions", body,
                       {"Content-Type": "application/json", "Accept": "text/event-stream"})
    response = connection.getresponse()
    if response.status != 200:
        raise RuntimeError(f"chat HTTP {response.status}: {response.read(2048)!r}")
    first_text = None
    text_parts = []
    while True:
        line = response.readline()
        if not line:
            break
        if not line.startswith(b"data: "):
            continue
        payload = line[6:].strip()
        if payload == b"[DONE]":
            break
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choices = event.get("choices") or []
        choice = choices[0] if choices else {}
        delta = choice.get("delta", {})
        for key in ("reasoning_content", "content"):
            value = delta.get(key)
            if value:
                if first_text is None:
                    first_text = time.perf_counter() - started
                text_parts.append(value)
        # The server's completion event is authoritative; it may keep the HTTP
        # connection open without emitting the optional [DONE] sentinel.
        if choice.get("finish_reason") is not None:
            break
    elapsed = time.perf_counter() - started
    connection.close()
    text = "".join(text_parts)
    return {"http": response.status, "ttft_first_text_s": first_text,
            "client_total_s": elapsed, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "text_chars": len(text)}


def start_one(arm, block, order):
    run = f"block-{block}-{order}-{arm}"
    config_path = OUT / f"{run}.json"
    log_path = OUT / f"{run}.log"
    map_path = OUT / f"{run}.residency.csv"
    args = ["--pack", str(PACK), "--native", str(MODEL), "--ple-gguf", str(PLE),
            "--expert-profile", str(PROFILE), "--expert-cache", "3000", "--prefill", "128",
            "--spec", "2", "--max-context", "8192", "--mmap-experts", "--prompt-cache", "0",
            "--vram-reserve-mib", "3072", "--pcie-frac", "0.55", "--no-prefill-borrow",
            "--pool-workers", "8", "--suffix-draft", "0", "--spec-min-p", "0"]
    if arm == "ninfer":
        args += ["--expert-backend", "ninfer", "--expert-backend-strict"]
    config = {"exe": str(ENGINE), "args": args, "cwd": str(ROOT), "tokenizer": str(TOKENIZER),
              "model_name": f"E2 matched-residency {arm}", "log": str(log_path),
              "lib_dirs": ["/usr/local/cuda-12/lib64"]}
    config_path.write_text(json.dumps(config))
    env = os.environ.copy()
    env["STRATA_RESIDENCY_DUMP"] = str(map_path)
    env["CUDA_MODULE_LOADING"] = "EAGER"
    with log_path.open("w") as log:
        proc = subprocess.Popen([sys.executable, str(ROOT / "serve/server.py"), "--engine", "strata",
                                 "--config", str(config_path), "--port", str(PORT)],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=False)
    try:
        deadline = time.monotonic() + 300
        ready = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited {proc.returncode}; see {log_path}")
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                    ready = True
                    break
            except OSError:
                time.sleep(0.5)
        if not ready:
            raise TimeoutError(f"server did not open port; see {log_path}")
        # A complete identical warmup compiles/captures the paths and stabilizes
        # the static profile cache before the measured request.
        warm = post_chat()
        measured = post_chat()
        return {"run": run, "arm": arm, "warmup": warm, "measured": measured,
                "residency_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
                "log": str(log_path)}
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output directory (default: prior paired-screen directory)")
    args = parser.parse_args()
    global OUT
    OUT = args.out.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261025)
    rows = []
    for block in range(1, 4):
        order = ["ninfer", "strata"]
        rng.shuffle(order)
        for position, arm in enumerate(order, 1):
            row = start_one(arm, block, position)
            rows.append(row)
            (OUT / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(json.dumps(row, separators=(",", ":")), flush=True)
    maps = {row["residency_sha256"] for row in rows}
    if len(maps) != 1:
        raise SystemExit(f"resident-map hashes differ: {sorted(maps)}")
    print(f"all six starts used identical resident map: {next(iter(maps))}")


if __name__ == "__main__":
    main()
