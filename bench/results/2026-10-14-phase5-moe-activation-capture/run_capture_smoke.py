#!/usr/bin/env python3
"""Run one short loopback request and validate the bounded MoE capture."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from benchmark_control import request


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    cfg["log"] = str((args.output / "engine.log").resolve())
    cfg["env"] = dict(cfg.get("env", {}))
    capture_path = (args.output / "capture.jsonl").resolve()
    cfg["env"].update({
        "STRATA_CAPTURE_MOE_PATH": str(capture_path),
        "STRATA_CAPTURE_MOE_LAYER": "0",
        "STRATA_CAPTURE_MOE_ROWS": "2",
    })
    config_path = args.output / "server-config.json"
    config_path.write_text(json.dumps(cfg, indent=2) + "\n")
    base = f"http://127.0.0.1:{cfg['port']}"
    server = subprocess.Popen(
        [sys.executable, "-m", "serve.server", "--engine", "strata", "--config",
         str(config_path.resolve()), "--host", "127.0.0.1", "--port", str(cfg["port"])],
        cwd=cfg["cwd"], env=os.environ | cfg["env"],
    )
    result = {"status": "not_run", "capture": str(capture_path)}
    try:
        deadline = time.monotonic() + 240
        while True:
            if server.poll() is not None:
                raise RuntimeError(f"server exited before readiness: {server.returncode}")
            try:
                health = request(base, "/health", timeout=5)
                if health.get("model"):
                    break
            except (urllib.error.URLError, OSError):
                if time.monotonic() >= deadline:
                    raise TimeoutError("server readiness deadline")
                time.sleep(0.5)
        response = request(base, "/v1/chat/completions", {
            "model": health["model"], "messages": [{"role": "user", "content": "Reply READY."}],
            "temperature": 0, "max_tokens": 8,
            "chat_template_kwargs": {"enable_thinking": False},
        }, timeout=600)
        lines = capture_path.read_text().splitlines()
        records = [json.loads(line) for line in lines]
        if len(records) < 2 or records[0].get("format") != "strata-moe-dispatch-v2":
            raise RuntimeError("capture did not contain a header and an activation row")
        width = int(records[0]["n_embd"])
        for row in records[1:]:
            if (row["layer"] != 0 or "dispatch" not in row or len(row["activation"]) != width or
                    len(row["ids"]) != row["k"] or len(row["route_kind"]) != row["k"] or
                    any(kind not in (-1, 0, 1, 2) for kind in row["route_kind"]) or
                    not all(math.isfinite(v) for v in row["activation"])):
                raise RuntimeError("capture row failed its geometry, route, or finite-value checks")
        result.update(status="pass", model=health["model"], response=response,
                      capture_rows=len(records) - 1, n_embd=width,
                      route_ids=records[1]["ids"], route_kind=records[1]["route_kind"])
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return 0
    except Exception as exc:
        result.update(status="fail", reason=f"{type(exc).__name__}: {exc}")
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
