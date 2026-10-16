#!/usr/bin/env python3
"""Run one same-service short/long/short Coder sequence at a chosen swap cap."""
import argparse
import hashlib
import json
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tools/integration")]
from tools.integration.accepted_prefix_parity import parse_hashes, STATE_KEYS
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

BASE = ROOT / "bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7"
MODEL = Path("/home/calvin/models/strata-orin-validation")


def replace_option(argv, name, value):
    if name in argv:
        argv[argv.index(name) + 1] = str(value)
    else:
        argv.extend((name, str(value)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapt-every", type=int, required=True)
    parser.add_argument("--adapt-swaps", type=int, required=True)
    parser.add_argument("--continuations", type=int, default=0,
                        help="extra identical short requests after short/long/short")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.continuations < 0:
        parser.error("--continuations must be non-negative")
    args.output.mkdir(parents=True, exist_ok=False)

    cfg = json.loads((BASE / "baseline-mtp0-config.json").read_text())
    argv = list(cfg["args"])
    replace_option(argv, "--adapt-every", args.adapt_every)
    replace_option(argv, "--adapt-swaps", args.adapt_swaps)
    if "--adapt-accepted-only" not in argv:
        argv.append("--adapt-accepted-only")
    if "--expert-cache-cpu-order" in argv:
        raise RuntimeError("CPU-order option is incompatible with the native Coder pack")

    tokenizer_path = Path(cfg["tokenizer"])
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / "chat_template.jinja")
    workload = json.loads((BASE / "workloads.json").read_text())["workloads"][0]
    long_ids = tokenizer.encode(template.render(workload["messages"], enable_thinking=False), parse_special=True)
    assert len(long_ids) == 2048, len(long_ids)
    prompts = [("short-512", long_ids[-512:]), ("long-2048", long_ids),
               ("short-512-recovery", long_ids[-512:])]
    prompts.extend((f"short-512-continuation-{index + 1}", long_ids[-512:])
                   for index in range(args.continuations))

    log = args.output / "service.log"
    env = child_env(cfg)
    env.update({
        "STRATA_STATE_HASH": "1", "STRATA_STATE_HASH_GDN": "1",
        "STRATA_ACCEPTED_PREFIX_TRACE": "1", "STRATA_INTEGRATION_TRACE": "1",
        "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_CAPTURE_MOE_LAYER": "0",
        "STRATA_CAPTURE_MOE_ROWS": "128", "STRATA_CAPTURE_MOE_START_ROW": "0",
        "STRATA_CAPTURE_MOE_PATH": str((args.output / "layer0.jsonl").resolve()),
        "STRATA_VERIFY_ADAPT_SWAPS": "1",
    })
    engine = StrataEngine(cfg["exe"], argv, cwd=cfg["cwd"], log=str(log), env=env)
    requests = []
    try:
        for name, prompt in prompts:
            ids = [int(token) for token in engine.generate(prompt, 16, {"temperature": 0}, threading.Event())
                   if token is not None]
            hashes = parse_hashes(log)
            if len(hashes) != len(requests) + 1:
                raise RuntimeError(f"expected {len(requests) + 1} state records, found {len(hashes)}")
            requests.append({"name": name, "prompt_tokens": len(prompt), "ids": ids,
                             "state": hashes[-1]})
            (args.output / "requests.json").write_text(json.dumps({"requests": requests}, indent=2) + "\n")
    finally:
        engine.close()

    captured = [json.loads(line) for line in (args.output / "layer0.jsonl").read_text().splitlines()]
    if not captured or captured[0].get("format") != "strata-moe-dispatch-v2":
        raise RuntimeError("missing layer-0 dispatch capture")
    rows = captured[1:]
    route = {"rows": len(rows)}
    if len(rows) >= 66:
        initial, long_rows, recovery = rows[:22], rows[22:44], rows[44:66]
        route.update({
            "first_seven_activation_equal": sum(a["activation"] == b["activation"]
                                                   for a, b in zip(initial[:7], recovery[:7])),
            "first_seven_expert_ids_equal": sum(a["ids"] == b["ids"]
                                                  for a, b in zip(initial[:7], recovery[:7])),
            "first_seven_owner_flips": sum(x != y for a, b in zip(initial[:7], recovery[:7])
                                             for x, y in zip(a["route_kind"], b["route_kind"])),
            "later_activation_differences": sum(a["activation"] != b["activation"]
                                                  for a, b in zip(initial[7:], recovery[7:])),
        })
    state_changes = [key for key in STATE_KEYS if requests[0]["state"][key] != requests[2]["state"][key]]
    results = {
        "adapt_every": args.adapt_every, "adapt_swaps": args.adapt_swaps,
        "prompt_sha256": {
            "short": hashlib.sha256(json.dumps(list(prompts[0][1])).encode()).hexdigest(),
            "long": hashlib.sha256(json.dumps(long_ids).encode()).hexdigest(),
        },
        "requests": requests, "recovery_token_differences": sum(a != b for a, b in
                                                                  zip(requests[0]["ids"], requests[2]["ids"])),
        "changed_state_keys": state_changes, "route": route,
        "adaptive_byte_verification_passes": log.read_text().count("adaptive swap byte verification passed"),
        "adaptive_residency_verification_passes": log.read_text().count("adaptive residency table verification passed"),
        "binary_sha256": hashlib.sha256(Path(cfg["exe"]).read_bytes()).hexdigest(),
        "model_identity": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
    }
    (args.output / "analysis.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"adapt_every": args.adapt_every, "adapt_swaps": args.adapt_swaps,
                      "recovery_token_differences": results["recovery_token_differences"],
                      "changed_state_keys": state_changes, "route": route}, indent=2))


if __name__ == "__main__":
    main()
