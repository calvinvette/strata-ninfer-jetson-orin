#!/usr/bin/env python3
"""Dump Coder GDN FP32 state after an initial short prompt or post-long recovery."""
import argparse
import hashlib
import json
import struct
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tools/integration")]
from tools.integration.accepted_prefix_parity import parse_hashes
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

BASE = ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check"


def replace_option(argv, name, value):
    if name in argv:
        argv[argv.index(name) + 1] = str(value)
    else:
        argv.extend((name, str(value)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("initial", "post-long-recovery"), required=True)
    parser.add_argument("--adapt-every", type=int, required=True)
    parser.add_argument("--adapt-swaps", type=int, default=8)
    parser.add_argument("--cpu-q8-1-dot", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    cfg = json.loads((BASE / "config.json").read_text())
    argv = list(cfg["args"])
    replace_option(argv, "--adapt-every", args.adapt_every)
    replace_option(argv, "--adapt-swaps", args.adapt_swaps)
    if "--adapt-accepted-only" not in argv:
        argv.append("--adapt-accepted-only")

    tokenizer_path = Path(cfg["tokenizer"])
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / "chat_template.jinja")
    workload = json.loads((BASE / "workloads.json").read_text())["workloads"][0]
    long_ids = tokenizer.encode(template.render(workload["messages"], enable_thinking=False), parse_special=True)
    assert len(long_ids) == 2048, len(long_ids)
    short_ids = long_ids[-512:]

    dump_path = (args.output / "gdn-state.f32").resolve()
    log = args.output / "service.log"
    env = child_env(cfg)
    env.update({
        "STRATA_STATE_HASH": "1",
        "STRATA_STATE_HASH_GDN": "1",
        "STRATA_ACCEPTED_PREFIX_TRACE": "1",
        "STRATA_INTEGRATION_TRACE": "1",
        "STRATA_PREFILL_CPU_SHARE": "0",
        "STRATA_VERIFY_ADAPT_SWAPS": "1",
        "STRATA_STATE_DUMP_GDN": str(dump_path),
        "STRATA_STATE_DUMP_GDN_AT": "527",
    })
    if args.cpu_q8_1_dot:
        env["STRATA_NATIVE_CPU_Q8_1_DOT"] = "1"

    engine = StrataEngine(cfg["exe"], argv, cwd=cfg["cwd"], log=str(log), env=env)
    requests = []
    sequence = ([('long-2048', long_ids), ('short-512-recovery', short_ids)]
                if args.mode == "post-long-recovery" else [('short-512', short_ids)])
    try:
        for name, prompt in sequence:
            ids = [int(token) for token in engine.generate(prompt, 16, {"temperature": 0}, threading.Event())
                   if token is not None]
            hashes = parse_hashes(log)
            if len(hashes) != len(requests) + 1:
                raise RuntimeError(f"expected {len(requests) + 1} state records, found {len(hashes)}")
            requests.append({"name": name, "prompt_tokens": len(prompt), "ids": ids, "state": hashes[-1]})
            (args.output / "requests.json").write_text(json.dumps({"requests": requests}, indent=2) + "\n")
    finally:
        engine.close()

    if not dump_path.is_file():
        raise RuntimeError("service did not emit the requested L=527 GDN state dump")
    raw = dump_path.read_bytes()
    if len(raw) < 32:
        raise RuntimeError("truncated GDN dump header")
    magic, cells, layers, floats_per_layer = struct.unpack("<8sQQQ", raw[:32])
    if magic != b"STGDN01\0" or cells != 527 or len(raw) != 32 + layers * floats_per_layer * 4:
        raise RuntimeError(f"invalid GDN dump geometry: magic={magic!r}, L={cells}, layers={layers}, floats/layer={floats_per_layer}, bytes={len(raw)}")

    result = {
        "mode": args.mode,
        "adapt_every": args.adapt_every,
        "adapt_swaps": args.adapt_swaps,
        "accepted_only": True,
        "cpu_q8_1_dot": args.cpu_q8_1_dot,
        "prompt_sha256": hashlib.sha256(json.dumps(list(short_ids)).encode()).hexdigest(),
        "dump": {"path": dump_path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                 "L": cells, "layers": layers, "floats_per_layer": floats_per_layer,
                 "total_floats": layers * floats_per_layer, "bytes": len(raw)},
        "requests": requests,
        "adaptive_byte_verifications": log.read_text().count("adaptive swap byte verification passed"),
        "adaptive_residency_verifications": log.read_text().count("adaptive residency table verification passed"),
        "binary_sha256": hashlib.sha256(Path(cfg["exe"]).read_bytes()).hexdigest(),
        "model_identity": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
    }
    (args.output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"mode": args.mode, "dump": result["dump"],
                      "requests": [{"name": r["name"], "tokens": len(r["ids"])} for r in requests],
                      "swap_verifications": [result["adaptive_byte_verifications"],
                                             result["adaptive_residency_verifications"]]}, indent=2))


if __name__ == "__main__":
    main()
