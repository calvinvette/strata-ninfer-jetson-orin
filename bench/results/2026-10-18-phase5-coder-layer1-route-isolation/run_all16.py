#!/usr/bin/env python3
"""Capture all 16 generated positions in the Coder CPU/mirror/GPU route diagnostic."""
import argparse
import hashlib
import json
import re
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
import sys
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tools/integration")]
from tools.integration.accepted_prefix_parity import STATE_KEYS
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env


def replace_option(argv, name, value):
    if name in argv:
        argv[argv.index(name) + 1] = str(value)
    else:
        argv.extend((name, str(value)))


def state_hashes(path):
    found = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        marker = " state={STATE_HASH "
        if "ACCEPTED_PREFIX " not in line or marker not in line:
            continue
        body = line.split(marker, 1)[1].split("}", 1)[0]
        fields = dict(re.findall(r"(\w+)=([0-9a-f,-]+)", body))
        if not set(STATE_KEYS) <= fields.keys():
            raise RuntimeError("incomplete accepted-prefix state fingerprint")
        found.append({key: fields[key] for key in STATE_KEYS})
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=("cpu_default", "cpu_mirror", "gpu_layer1"), required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((HERE / "config.json").read_text())
    argv = list(cfg["args"])
    replace_option(argv, "--adapt-every", 0)
    replace_option(argv, "--adapt-swaps", 0)
    replace_option(argv, "--prompt-cache", 0)
    profile = ROOT / "data/expert-profile-coder.bin"
    if a.arm == "gpu_layer1":
        profile = HERE / "layer1-gpu-profile.bin"
    replace_option(argv, "--expert-profile", profile)
    env = child_env(cfg)
    env.update({"STRATA_STATE_HASH": "1", "STRATA_STATE_HASH_GDN": "1",
                "STRATA_ACCEPTED_PREFIX_TRACE": "1", "STRATA_INTEGRATION_TRACE": "1",
                "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_VERIFY_ADAPT_SWAPS": "1",
                "STRATA_CAPTURE_MOE_LAYER": "-1", "STRATA_CAPTURE_MOE_ROWS": "768",
                "STRATA_CAPTURE_MOE_START_ROW": "0",
                "STRATA_CAPTURE_MOE_PATH": str((a.output / "routes-all-layers.jsonl").resolve()),
                "STRATA_CAPTURE_MOE_OUTPUT_PATH": str((a.output / "cpu-outputs-layer1.jsonl").resolve()),
                "STRATA_CAPTURE_MOE_OUTPUT_LAYER": "1",
                "STRATA_VERIFY_DUMP_GDN_LAYER": "1",
                "STRATA_VERIFY_DUMP_GDN_PATH": str((a.output / "combined-moe.bin").resolve())})
    if a.arm == "cpu_mirror":
        env["STRATA_NATIVE_CPU_Q8_1_DOT"] = "1"
    tok_dir = Path(cfg["tokenizer"])
    tokenizer = load_tokenizer(tok_dir)
    template = ChatTemplate(tok_dir / "chat_template.jinja")
    workload = json.loads((HERE / "workloads.json").read_text())["workloads"][0]
    long_ids = tokenizer.encode(template.render(workload["messages"], enable_thinking=False), parse_special=True)
    prompt = [int(x) for x in long_ids[-512:]]
    if len(prompt) != 512:
        raise RuntimeError(f"expected exact 512-token prompt, got {len(prompt)}")
    log = a.output / "service.log"
    engine = StrataEngine(cfg["exe"], argv, cwd=cfg["cwd"], log=str(log), env=env)
    try:
        ids = [int(token) for token in engine.generate(prompt, 16, {"temperature": 0}, threading.Event())
               if token is not None]
    finally:
        engine.close()
    if len(ids) != 16:
        raise RuntimeError(f"expected 16 completion tokens, got {len(ids)}")
    hashes = state_hashes(log)
    if len(hashes) < 16:
        raise RuntimeError(f"expected accepted-prefix state trace, got {len(hashes)} records")
    route_lines = (a.output / "routes-all-layers.jsonl").read_text().splitlines()
    route = [json.loads(line) for line in route_lines[1:]]
    if len(route) != 768:
        raise RuntimeError(f"expected 768 capture rows, got {len(route)}")
    if json.loads(route_lines[0]).get("format") != "strata-moe-dispatch-v3":
        raise RuntimeError("route capture is missing the position-keyed format")
    per_layer = {}
    for row in route:
        per_layer.setdefault(row["layer"], set()).add(row["position"])
        if row.get("position", -1) < 0 or row.get("token_id", -1) < 0:
            raise RuntimeError("route capture has an invalid absolute token key")
    if len(per_layer) != 48 or any(len(positions) != 16 for positions in per_layer.values()):
        raise RuntimeError(f"capture did not span 16 positions on 48 layers: {[(k, len(v)) for k,v in per_layer.items()]}")
    cpu_lines = (a.output / "cpu-outputs-layer1.jsonl").read_text().splitlines()
    if not cpu_lines or json.loads(cpu_lines[0]).get("format") != "strata-moe-cpu-output-v2":
        raise RuntimeError("missing CPU output capture")
    cpu_rows = [json.loads(line) for line in cpu_lines[1:]]
    if any(row.get("layer") != 1 for row in cpu_rows):
        raise RuntimeError("CPU output capture included a non-layer-1 row")
    (a.output / "requests.json").write_text(json.dumps({
        "arm": a.arm, "prompt_tokens": len(prompt), "prompt_sha256": hashlib.sha256(
            b"".join(int(x).to_bytes(4, "little", signed=True) for x in prompt)).hexdigest(),
        "completion_ids": ids, "state": hashes[-1], "accepted_prefix_records": len(hashes),
        "cpu_output_records": len(cpu_rows), "captured_positions_per_layer": 16,
        "captured_layers": 48, "profile": str(profile),
        "profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest()}, indent=2) + "\n")
    print(f"{a.arm}: passed; route rows={len(route)}, layer-1 CPU outputs={len(cpu_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
