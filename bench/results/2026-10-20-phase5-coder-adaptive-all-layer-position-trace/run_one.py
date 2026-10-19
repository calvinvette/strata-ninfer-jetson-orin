#!/usr/bin/env python3
"""Run one same-service Coder sequence with fixed or adaptive residency."""
import argparse
import hashlib
import json
import struct
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
    parser.add_argument("--spec", type=int,
                        help="override the configured verifier window for a prompt-tail localization ablation")
    parser.add_argument("--capture-moe-positions", default="511",
                        help="comma-separated increasing absolute positions for the all-layer expert trace")
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
                        help="capture the GDN pre/post state at selected positions for this layer")
    parser.add_argument("--gdn-state-output", type=Path,
                        help="external output path for the raw pre/post GDN state records")
    parser.add_argument("--gdn-state-positions", default="511",
                        help="comma-separated increasing token positions to capture (default: 511)")
    parser.add_argument("--trace-prefill-gdn-state-layer", type=int,
                        help="emit full GDN-state hashes after each prefill chunk for this model layer")
    parser.add_argument("--prefill-gdn-state-output", type=Path,
                        help="optional external raw end-of-prompt GDN snapshots for the traced layer")
    parser.add_argument("--capture-gdn-commit-state-layer", type=int,
                        help="capture committed GDN state after accepted windows at selected positions")
    parser.add_argument("--gdn-commit-state-positions", default="",
                        help="comma-separated increasing accepted positions to capture")
    parser.add_argument("--gdn-commit-state-output", type=Path,
                        help="external output path for committed GDN state records")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.continuations < 0:
        parser.error("--continuations must be non-negative")
    if args.spec is not None and args.spec < 0:
        parser.error("--spec must be non-negative")
    try:
        capture_moe_positions = [int(value) for value in args.capture_moe_positions.split(",")]
    except ValueError:
        parser.error("--capture-moe-positions must be comma-separated non-negative integers")
    if not capture_moe_positions or any(value < 0 for value in capture_moe_positions) or \
            capture_moe_positions != sorted(set(capture_moe_positions)):
        parser.error("--capture-moe-positions must be strictly increasing non-negative integers")
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
    if args.trace_prefill_gdn_state_layer is not None and args.trace_prefill_gdn_state_layer < 0:
        parser.error("prefill GDN state trace layer must be non-negative")
    if args.prefill_gdn_state_output is not None and args.trace_prefill_gdn_state_layer is None:
        parser.error("prefill GDN state output requires --trace-prefill-gdn-state-layer")
    if (args.capture_gdn_commit_state_layer is None) != (args.gdn_commit_state_output is None):
        parser.error("GDN commit capture requires both --capture-gdn-commit-state-layer and --gdn-commit-state-output")
    if args.capture_gdn_commit_state_layer is None and args.gdn_commit_state_positions:
        parser.error("GDN commit positions require --capture-gdn-commit-state-layer")
    try:
        gdn_commit_positions = [int(value) for value in args.gdn_commit_state_positions.split(",") if value]
    except ValueError:
        parser.error("--gdn-commit-state-positions must be comma-separated non-negative integers")
    if args.capture_gdn_commit_state_layer is not None and (
            args.capture_gdn_commit_state_layer < 0 or not gdn_commit_positions or
            any(value < 0 for value in gdn_commit_positions) or
            gdn_commit_positions != sorted(set(gdn_commit_positions))):
        parser.error("GDN commit capture requires a non-negative layer and increasing non-negative positions")
    if (args.capture_verify_gdn_state_layer is None) != (args.gdn_state_output is None):
        parser.error("GDN state capture requires both --capture-verify-gdn-state-layer and --gdn-state-output")
    try:
        state_positions = [int(value) for value in args.gdn_state_positions.split(",")]
    except ValueError:
        parser.error("--gdn-state-positions must be comma-separated non-negative integers")
    if not state_positions or any(value < 0 for value in state_positions) or state_positions != sorted(set(state_positions)):
        parser.error("--gdn-state-positions must be strictly increasing non-negative integers")
    args.output.mkdir(parents=True, exist_ok=False)

    cfg = json.loads((BASE / "config.json").read_text())
    argv = list(cfg["args"])
    configured_spec = int(argv[argv.index("--spec") + 1])
    if args.spec is not None:
        replace_option(argv, "--spec", args.spec)
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
    capture_path = args.output / ("all-layer-position511.jsonl" if capture_moe_positions == [511]
                                  else "all-layer-selected-positions.jsonl")
    env.update({
        "STRATA_STATE_HASH": "1", "STRATA_STATE_HASH_GDN": "1",
        "STRATA_ACCEPTED_PREFIX_TRACE": "1", "STRATA_INTEGRATION_TRACE": "1",
        "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_CAPTURE_MOE_LAYER": "-1",
        "STRATA_CAPTURE_MOE_ROWS": "4096" if capture_moe_positions != [511] else "96",
        "STRATA_CAPTURE_MOE_START_ROW": "0",
        "STRATA_CAPTURE_MOE_POSITIONS": ",".join(map(str, capture_moe_positions)),
        "STRATA_CAPTURE_MOE_PATH": str(capture_path.resolve()),
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
            "STRATA_VERIFY_DUMP_GDN_STATE_POSITIONS": ",".join(map(str, state_positions)),
        })
    if args.trace_prefill_gdn_state_layer is not None:
        env["STRATA_PREFILL_GDN_STATE_TRACE_LAYER"] = str(args.trace_prefill_gdn_state_layer)
    prefill_state_output = None
    if args.prefill_gdn_state_output is not None:
        prefill_state_output = args.prefill_gdn_state_output.expanduser().resolve()
        if prefill_state_output.exists():
            parser.error(f"prefill GDN state output already exists: {prefill_state_output}")
        prefill_state_output.parent.mkdir(parents=True, exist_ok=True)
        env["STRATA_PREFILL_GDN_STATE_TRACE_PATH"] = str(prefill_state_output)
    gdn_commit_state_output = None
    if args.gdn_commit_state_output is not None:
        gdn_commit_state_output = args.gdn_commit_state_output.expanduser().resolve()
        if gdn_commit_state_output.exists():
            parser.error(f"GDN commit state output already exists: {gdn_commit_state_output}")
        gdn_commit_state_output.parent.mkdir(parents=True, exist_ok=True)
        env.update({
            "STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER": str(args.capture_gdn_commit_state_layer),
            "STRATA_VERIFY_DUMP_GDN_COMMIT_PATH": str(gdn_commit_state_output),
            "STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS": ",".join(map(str, gdn_commit_positions)),
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

    gdn_commit_capture = None
    if gdn_commit_state_output is not None:
        header = struct.Struct("<8sIiqQQii")
        raw = gdn_commit_state_output.read_bytes()
        offset = 0
        observed = {}
        while offset < len(raw):
            if len(raw) - offset < header.size:
                raise RuntimeError("truncated committed GDN state header")
            magic, version, layer, position, recurrent, total, token, slot = header.unpack_from(raw, offset)
            offset += header.size
            if magic != b"STGCMT1\0" or version != 1 or layer != args.capture_gdn_commit_state_layer:
                raise RuntimeError("invalid committed GDN state record")
            if total < recurrent or len(raw) - offset < total * 4:
                raise RuntimeError("truncated committed GDN state payload")
            offset += total * 4
            observed[position] = observed.get(position, 0) + 1
        if not observed or any(count < 2 for count in observed.values()):
            raise RuntimeError(f"committed GDN positions were not captured in both short requests: {observed}")
        gdn_commit_capture = {
            "layer": args.capture_gdn_commit_state_layer,
            "path": str(gdn_commit_state_output),
            "bytes": len(raw),
            "requested_positions": gdn_commit_positions,
            "observed_records_per_position": observed,
        }

    if gdn_state_output is not None:
        header = struct.Struct("<8sIiqQQii")
        raw = gdn_state_output.read_bytes()
        offset = 0
        observed = {}
        while offset < len(raw):
            if len(raw) - offset < header.size:
                raise RuntimeError("truncated verifier GDN state diagnostic header")
            magic, version, layer, position, recurrent, total, token, reserved = header.unpack_from(raw, offset)
            offset += header.size
            if magic != b"STGSTAT1" or version != 1 or layer != args.capture_verify_gdn_state_layer or reserved != 0:
                raise RuntimeError("invalid verifier GDN state diagnostic record")
            if total < recurrent or len(raw) - offset < 2 * total * 4:
                raise RuntimeError("truncated verifier GDN state diagnostic payload")
            offset += 2 * total * 4
            observed[position] = observed.get(position, 0) + 1
        expected = {position: 2 for position in state_positions}
        if observed != expected:
            raise RuntimeError(f"verifier GDN state positions not observed twice in initial/recovery: {observed}; expected {expected}")

    captured = [json.loads(line) for line in capture_path.read_text().splitlines()]
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
        "configured_spec": configured_spec, "spec_override": args.spec,
        "capture_moe_positions": capture_moe_positions,
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
        "verify_gdn_commit_state_capture": gdn_commit_capture,
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
