#!/usr/bin/env python3
"""Run one same-service Coder sequence with fixed or adaptive residency."""
import argparse
import hashlib
import json
import re
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tools/integration")]
from tools.integration.accepted_prefix_parity import STATE_KEYS
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

BASE = Path(__file__).resolve().parent
MODEL = Path("/home/calvin/models/strata-orin-validation")


def replace_option(argv, name, value):
    if name in argv:
        argv[argv.index(name) + 1] = str(value)
    else:
        argv.extend((name, str(value)))


def parse_prefix_hashes(path):
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapt-every", type=int, required=True)
    parser.add_argument("--adapt-swaps", type=int, required=True)
    parser.add_argument("--continuations", type=int, default=0,
                        help="extra identical short requests after short/long/short")
    parser.add_argument("--prompt-cache", type=int,
                        help="override the configured prompt-cache capacity for this run")
    parser.add_argument("--capture-layer", type=int, default=1,
                        help="captured MoE layer; -1 captures every layer")
    parser.add_argument("--capture-rows", type=int, default=128,
                        help="maximum captured MoE activation rows")
    parser.add_argument("--capture-start-row", type=int, default=0,
                        help="skip this many captured rows before writing")
    parser.add_argument("--capture-cpu-output", action="store_true",
                        help="dump CPU-owned expert outputs from one service dispatch")
    parser.add_argument("--capture-output-layer", type=int, default=1)
    parser.add_argument("--capture-dispatch", type=int, default=1393)
    parser.add_argument("--capture-combined-moe", action="store_true",
                        help="capture the verifier's combined layer-1 FFN/MoE output")
    parser.add_argument("--cpu-q8-1-dot", action="store_true",
                        help="enable opt-in IQ2_S/Q2_0, IQ2_S/IQ4_NL and IQ3_XXS/IQ4_NL CPU Q8_1 scalar routes")
    parser.add_argument("--cpu-q8-1-pair",
                        help="enable one Q8_1 CPU expert pair, optionally scoped as pair@layer=N")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.continuations < 0:
        parser.error("--continuations must be non-negative")
    args.output.mkdir(parents=True, exist_ok=False)

    cfg = json.loads((BASE / "config.json").read_text())
    argv = list(cfg["args"])
    replace_option(argv, "--adapt-every", args.adapt_every)
    replace_option(argv, "--adapt-swaps", args.adapt_swaps)
    if args.prompt_cache is not None:
        replace_option(argv, "--prompt-cache", args.prompt_cache)
    adaptation_on = args.adapt_every > 0 and args.adapt_swaps > 0
    if adaptation_on and "--adapt-accepted-only" not in argv:
        argv.append("--adapt-accepted-only")
    elif not adaptation_on and "--adapt-accepted-only" in argv:
        del argv[argv.index("--adapt-accepted-only")]
    combined_dump = args.output / "combined-moe.bin" if args.capture_combined_moe else None
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
        "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_CAPTURE_MOE_LAYER": str(args.capture_layer),
        "STRATA_CAPTURE_MOE_ROWS": str(args.capture_rows),
        "STRATA_CAPTURE_MOE_START_ROW": str(args.capture_start_row),
        "STRATA_CAPTURE_MOE_PATH": str((args.output / "layer1.jsonl").resolve()),
        "STRATA_VERIFY_ADAPT_SWAPS": "1",
    })
    if args.capture_cpu_output:
        env.update({
            "STRATA_CAPTURE_MOE_OUTPUT_PATH": str((args.output / "cpu-outputs.jsonl").resolve()),
            "STRATA_CAPTURE_MOE_OUTPUT_LAYER": str(args.capture_output_layer),
            "STRATA_CAPTURE_MOE_OUTPUT_DISPATCH": str(args.capture_dispatch),
        })
    if combined_dump is not None:
        env.update({"STRATA_VERIFY_DUMP_GDN_LAYER": "1",
                    "STRATA_VERIFY_DUMP_GDN_PATH": str(combined_dump.resolve())})
    if args.cpu_q8_1_dot and args.cpu_q8_1_pair is not None:
        parser.error("choose either --cpu-q8-1-dot or --cpu-q8-1-pair")
    if args.cpu_q8_1_pair is not None and not re.fullmatch(
            r"(?:all|iq2_s/q2_0|iq2_s/iq4_nl|iq3_xxs/iq4_nl)(?:@layer=[0-9]+)?",
            args.cpu_q8_1_pair):
        parser.error("invalid Q8_1 pair selector")
    if args.cpu_q8_1_dot:
        env["STRATA_NATIVE_CPU_Q8_1_DOT"] = "1"
    elif args.cpu_q8_1_pair is not None:
        env["STRATA_NATIVE_CPU_Q8_1_DOT"] = args.cpu_q8_1_pair
    engine = StrataEngine(cfg["exe"], argv, cwd=cfg["cwd"], log=str(log), env=env)
    requests = []
    previous_prefix_hash_count = 0
    try:
        for name, prompt in prompts:
            ids = [int(token) for token in engine.generate(prompt, 16, {"temperature": 0}, threading.Event())
                   if token is not None]
            hashes = parse_prefix_hashes(log)
            if len(hashes) <= previous_prefix_hash_count:
                raise RuntimeError(f"expected new accepted-prefix hashes after request {len(requests) + 1}, "
                                   f"found {len(hashes)} total")
            previous_prefix_hash_count = len(hashes)
            requests.append({"name": name, "prompt_tokens": len(prompt), "ids": ids,
                             "state": hashes[-1]})
            (args.output / "requests.json").write_text(json.dumps({"requests": requests}, indent=2) + "\n")
    finally:
        engine.close()

    captured = [json.loads(line) for line in (args.output / "layer1.jsonl").read_text().splitlines()]
    if not captured or captured[0].get("format") != "strata-moe-dispatch-v3":
        raise RuntimeError("missing layer-0 dispatch capture")
    rows = captured[1:]
    cpu_output_rows = 0
    if args.capture_cpu_output:
        output_capture = args.output / "cpu-outputs.jsonl"
        if not output_capture.exists():
            raise RuntimeError("requested CPU expert output capture was not produced")
        cpu_output_lines = output_capture.read_text().splitlines()
        if not cpu_output_lines or json.loads(cpu_output_lines[0]).get("format") not in (
                "strata-moe-cpu-output-v1", "strata-moe-cpu-output-v2"):
            raise RuntimeError("CPU expert output capture has an invalid header")
        cpu_output_rows = len(cpu_output_lines) - 1
        if cpu_output_rows == 0:
            raise RuntimeError("requested dispatch had no CPU-owned expert outputs")
    if combined_dump is not None and (not combined_dump.exists() or combined_dump.stat().st_size == 0):
        raise RuntimeError("requested verifier layer-1 combined-output capture was not produced")
    route = {"rows": len(rows)}
    if args.capture_layer == 1 and len(rows) >= 66:
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
        "prompt_cache": args.prompt_cache if args.prompt_cache is not None else
            int(argv[argv.index("--prompt-cache") + 1]) if "--prompt-cache" in argv else None,
        "cpu_q8_1_dot": args.cpu_q8_1_dot,
        "cpu_q8_1_pair": args.cpu_q8_1_pair,
        "capture_layer": args.capture_layer,
        "capture_rows": args.capture_rows,
        "capture_start_row": args.capture_start_row,
        "capture_cpu_output": args.capture_cpu_output,
        "capture_output_layer": args.capture_output_layer if args.capture_cpu_output else None,
        "capture_dispatch": args.capture_dispatch if args.capture_cpu_output else None,
        "captured_cpu_output_rows": cpu_output_rows,
        "capture_combined_moe": args.capture_combined_moe,
        "combined_moe_dump_bytes": combined_dump.stat().st_size if combined_dump is not None else 0,
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
