#!/usr/bin/env python3
"""Run one same-service Coder sequence with fixed or adaptive residency."""
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

BASE = Path("/home/calvin/workspace/strata-ninfer-jetson-orin/bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7")
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
    parser.add_argument("--dump-gdn-occurrence", type=int,
                        help="optionally dump GDN state at L=512 on this matching request occurrence")
    parser.add_argument("--capture-cpu-output-layer", type=int,
                        help="capture CPU expert rows from one verifier/prefill dispatch at this layer")
    parser.add_argument("--capture-cpu-output-dispatch", type=int,
                        help="select the dispatch ID for the optional CPU expert output capture")
    parser.add_argument("--capture-verify-moe-layer", type=int,
                        help="capture verifier router weights and all expert rows at position 511 for this layer")
    parser.add_argument("--capture-verify-gdn-layer", type=int,
                        help="capture verifier GDN intermediates at position 511 for this layer")
    parser.add_argument("--capture-verify-gdn-state-layer", type=int,
                        help="capture the GDN pre/post persistent state at position 511 for this layer")
    parser.add_argument("--gdn-state-output", type=Path,
                        help="external output path for the raw pre/post GDN state records")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.continuations < 0:
        parser.error("--continuations must be non-negative")
    if args.dump_gdn_occurrence is not None and args.dump_gdn_occurrence < 1:
        parser.error("--dump-gdn-occurrence must be positive")
    if args.dump_gdn_occurrence is not None and args.dump_gdn_occurrence > 2 + args.continuations:
        parser.error("dump occurrence exceeds the number of 512-token requests; add continuations or lower the occurrence")
    if (args.capture_cpu_output_layer is None) != (args.capture_cpu_output_dispatch is None):
        parser.error("CPU output capture requires both --capture-cpu-output-layer and --capture-cpu-output-dispatch")
    if args.capture_cpu_output_layer is not None and (
            args.capture_cpu_output_layer < 0 or args.capture_cpu_output_dispatch < 0):
        parser.error("CPU output capture layer and dispatch must be non-negative")
    if args.capture_verify_moe_layer is not None and args.capture_verify_moe_layer < 0:
        parser.error("verifier MoE capture layer must be non-negative")
    if args.capture_verify_gdn_layer is not None and args.capture_verify_gdn_layer < 0:
        parser.error("verifier GDN capture layer must be non-negative")
    if args.capture_verify_gdn_state_layer is not None and args.capture_verify_gdn_state_layer < 0:
        parser.error("verifier GDN state capture layer must be non-negative")
    if (args.capture_verify_gdn_state_layer is None) != (args.gdn_state_output is None):
        parser.error("GDN state capture requires both --capture-verify-gdn-state-layer and --gdn-state-output")
    args.output.mkdir(parents=True, exist_ok=False)

    cfg = json.loads((BASE / "config.json").read_text())
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
        "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_CAPTURE_MOE_LAYER": "-1",
        "STRATA_CAPTURE_MOE_ROWS": "96", "STRATA_CAPTURE_MOE_START_ROW": "0",
        "STRATA_CAPTURE_MOE_POSITION": "511",
        "STRATA_CAPTURE_MOE_PATH": str((args.output / "all-layer-position511.jsonl").resolve()),
        "STRATA_VERIFY_ADAPT_SWAPS": "1",
        "STRATA_NATIVE_CPU_Q8_1_DOT": "all",
    })
    if args.dump_gdn_occurrence is not None:
        env.update({
            "STRATA_STATE_DUMP_GDN": str((args.output / "gdn-state-L512.bin").resolve()),
            "STRATA_STATE_DUMP_GDN_AT": "512",
            "STRATA_STATE_DUMP_GDN_OCCURRENCE": str(args.dump_gdn_occurrence),
        })
    if args.capture_cpu_output_layer is not None:
        env.update({
            "STRATA_CAPTURE_MOE_OUTPUT_PATH": str((args.output / "cpu-moe-outputs.jsonl").resolve()),
            "STRATA_CAPTURE_MOE_OUTPUT_LAYER": str(args.capture_cpu_output_layer),
            "STRATA_CAPTURE_MOE_OUTPUT_DISPATCH": str(args.capture_cpu_output_dispatch),
        })
    if args.capture_verify_moe_layer is not None:
        env.update({
            "STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER": str(args.capture_verify_moe_layer),
            "STRATA_VERIFY_DUMP_MOE_ROUTE_PATH": str((args.output / "verify-moe-routes.jsonl").resolve()),
            "STRATA_VERIFY_DUMP_MOE_ROUTE_POSITION": "511",
            "STRATA_VERIFY_DUMP_MOE_PARTS_LAYER": str(args.capture_verify_moe_layer),
            "STRATA_VERIFY_DUMP_MOE_PARTS_PATH": str((args.output / "verify-moe-parts.bin").resolve()),
            "STRATA_VERIFY_DUMP_MOE_PARTS_POSITION": "511",
            "STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER": str(args.capture_verify_moe_layer),
            "STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH": str((args.output / "verify-moe-output.bin").resolve()),
            "STRATA_VERIFY_DUMP_MOE_OUTPUT_POSITION": "511",
        })
    if args.capture_verify_gdn_layer is not None:
        env.update({
            "STRATA_VERIFY_DUMP_GDN_LAYER": str(args.capture_verify_gdn_layer),
            "STRATA_VERIFY_DUMP_GDN_PATH": str((args.output / "verify-gdn.bin").resolve()),
            "STRATA_VERIFY_DUMP_GDN_POSITION": "511",
        })
    gdn_state_output = None
    if args.gdn_state_output is not None:
        gdn_state_output = args.gdn_state_output.expanduser().resolve()
        if gdn_state_output.exists():
            parser.error(f"GDN state output already exists: {gdn_state_output}")
        gdn_state_output.parent.mkdir(parents=True, exist_ok=True)
        env.update({
            "STRATA_VERIFY_DUMP_GDN_STATE_LAYER": str(args.capture_verify_gdn_state_layer),
            "STRATA_VERIFY_DUMP_GDN_STATE_PATH": str(gdn_state_output),
            "STRATA_VERIFY_DUMP_GDN_STATE_POSITION": "511",
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

    captured = [json.loads(line) for line in (args.output / "all-layer-position511.jsonl").read_text().splitlines()]
    if not captured or captured[0].get("format") != "strata-moe-dispatch-v3":
        raise RuntimeError("missing current all-layer dispatch capture")
    rows = captured[1:]
    cpu_output_capture = None
    if args.capture_cpu_output_layer is not None:
        output_path = args.output / "cpu-moe-outputs.jsonl"
        if not output_path.is_file():
            raise RuntimeError("requested CPU expert output capture was not written")
        output_records = [json.loads(line) for line in output_path.read_text().splitlines()]
        output_rows = output_records[1:]
        target_rows = [row for row in output_rows
                       if row.get("layer") == args.capture_cpu_output_layer
                       and row.get("dispatch") == args.capture_cpu_output_dispatch
                       and row.get("position") == 511]
        if not target_rows:
            raise RuntimeError("CPU expert output capture missed the selected layer/dispatch at position 511")
        cpu_output_capture = {
            "layer": args.capture_cpu_output_layer,
            "dispatch": args.capture_cpu_output_dispatch,
            "rows": len(output_rows),
            "target_position_rows": len(target_rows),
            "position": 511,
        }
    verify_moe_capture = None
    if args.capture_verify_moe_layer is not None:
        route_path = args.output / "verify-moe-routes.jsonl"
        parts_path = args.output / "verify-moe-parts.bin"
        output_path = args.output / "verify-moe-output.bin"
        if not route_path.is_file() or not parts_path.is_file() or not output_path.is_file():
            raise RuntimeError("requested verifier MoE route/parts/output capture was not written")
        route_records = [json.loads(line) for line in route_path.read_text().splitlines()]
        selected_routes = [row for row in route_records[1:]
                           if row.get("layer") == args.capture_verify_moe_layer and row.get("position") == 511]
        if len(selected_routes) != 2:
            raise RuntimeError(f"expected initial and recovery verifier route rows at position 511, got {len(selected_routes)}")
        verify_moe_capture = {
            "layer": args.capture_verify_moe_layer,
            "position": 511,
            "route_rows": len(selected_routes),
            "parts_bytes": parts_path.stat().st_size,
            "output_bytes": output_path.stat().st_size,
        }
    verify_gdn_capture = None
    if args.capture_verify_gdn_layer is not None:
        gdn_path = args.output / "verify-gdn.bin"
        if not gdn_path.is_file():
            raise RuntimeError("requested verifier GDN capture was not written")
        verify_gdn_capture = {
            "layer": args.capture_verify_gdn_layer,
            "position": 511,
            "bytes": gdn_path.stat().st_size,
        }
    verify_gdn_state_capture = None
    if gdn_state_output is not None:
        if not gdn_state_output.is_file():
            raise RuntimeError("requested pre/post GDN state capture was not written")
        verify_gdn_state_capture = {
            "layer": args.capture_verify_gdn_state_layer,
            "position": 511,
            "path": str(gdn_state_output),
            "bytes": gdn_state_output.stat().st_size,
        }
    route = {"rows": len(rows),
             "layers": sorted({row["layer"] for row in rows}),
             "positions": sorted({row["position"] for row in rows})}
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
        "cpu_output_capture": cpu_output_capture,
        "verify_moe_capture": verify_moe_capture,
        "verify_gdn_capture": verify_gdn_capture,
        "verify_gdn_state_capture": verify_gdn_state_capture,
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
