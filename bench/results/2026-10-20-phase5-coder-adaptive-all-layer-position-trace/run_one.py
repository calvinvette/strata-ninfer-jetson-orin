#!/usr/bin/env python3
"""Run one same-service Coder sequence with fixed or adaptive residency."""
import argparse
import hashlib
import json
import math
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
    parser.add_argument("--capture-moe-rows", type=int, default=96,
                        help="maximum selected all-layer expert rows to retain (1-4096)")
    parser.add_argument("--continuations", type=int, default=0,
                        help="extra identical short requests after short/long/short")
    parser.add_argument("--sequence", choices=("short-long-short", "short-short-short"),
                        default="short-long-short",
                        help="same-service request history used for the recovery comparison")
    parser.add_argument("--generated-tokens", type=int, default=16,
                        help="maximum generated tokens per request (default: 16)")
    parser.add_argument("--workload-file", type=Path,
                        help="optional workload JSON (defaults to the pinned Phase 5 prompt set)")
    parser.add_argument("--workload-index", type=int, default=0,
                        help="workload entry index in --workload-file (default: 0)")
    parser.add_argument("--long-token-limit", type=int, default=0,
                        help="optional suffix length for the long prompt (0 keeps all encoded tokens)")
    parser.add_argument("--native-cpu-q8-1-dot", default="all",
                        help="opt-in CPU/CUDA Q8_1 arithmetic selector passed to the engine (default: all)")
    parser.add_argument("--native-cpu-q8-1-reciprocal-silu-layer", type=int,
                        help="opt-in reciprocal-SiLU expression for Q8_1 native experts at one layer")
    parser.add_argument("--native-cpu-q8-1-reciprocal-silu-expert", type=int,
                        help="optionally restrict reciprocal-SiLU to one model expert ID")
    parser.add_argument("--prompt-cache", type=int,
                        help="override the configured prompt-cache capacity for a cache ablation")
    parser.add_argument("--dump-gdn-occurrence", type=int,
                        help="optionally dump GDN state at L=512 on this matching request occurrence")
    parser.add_argument("--capture-cpu-output-layer", type=int,
                        help="capture CPU expert rows from one verifier/prefill dispatch at this layer")
    parser.add_argument("--capture-cpu-output-dispatch", type=int,
                        help="select the dispatch ID for the optional CPU expert output capture")
    parser.add_argument("--capture-cpu-output-position", type=int, default=511,
                        help="position to require in the selected CPU expert output dispatch (default: 511)")
    parser.add_argument("--capture-verify-moe-layer", type=int,
                        help="capture verifier router weights and all expert rows at selected positions for this layer")
    parser.add_argument("--verify-moe-positions", default="511",
                        help="comma-separated increasing verifier MoE diagnostic positions (default: 511)")
    parser.add_argument("--verify-moe-input-layers", choices=("same", "all"), default="same",
                        help="capture verifier MoE inputs at the selected MoE layer or all model layers")
    parser.add_argument("--capture-verify-gdn-layer", type=int,
                        help="capture verifier GDN intermediates at selected positions for this layer")
    parser.add_argument("--verify-gdn-positions", default="511",
                        help="comma-separated increasing verifier GDN diagnostic positions (default: 511)")
    parser.add_argument("--capture-verify-gdn-state-layer", type=int,
                        help="capture the GDN pre/post state at selected positions for this layer")
    parser.add_argument("--capture-boundary-layer", type=int,
                        help="capture residual/hyperconnection values after this layer and at the next layer's first read")
    parser.add_argument("--boundary-position", type=int, default=511,
                        help="absolute position for the optional residual-boundary capture (default: 511)")
    parser.add_argument("--gdn-state-output", type=Path,
                        help="external output path for the raw pre/post GDN state records")
    parser.add_argument("--gdn-state-positions", default="511",
                        help="comma-separated increasing token positions to capture (default: 511)")
    parser.add_argument("--trace-prefill-gdn-state-layer", type=int,
                        help="emit full GDN-state hashes after each prefill chunk for this model layer")
    parser.add_argument("--prefill-gdn-state-output", type=Path,
                        help="optional external raw end-of-prompt GDN snapshots for the traced layer")
    parser.add_argument("--capture-gdn-commit-state-layer",
                        help="GDN model layer or 'all' to capture committed state after accepted windows")
    parser.add_argument("--gdn-commit-state-positions", default="",
                        help="comma-separated increasing accepted positions to capture")
    parser.add_argument("--gdn-commit-state-output", type=Path,
                        help="external output path for committed GDN state records")
    parser.add_argument("--capture-gr-read-layer", type=int,
                        help="capture fused GR-read outputs at this verifier layer")
    parser.add_argument("--gr-read-position", type=int,
                        help="absolute token position for the fused GR-read capture")
    parser.add_argument("--gr-read-output", type=Path,
                        help="external output path for the fused GR-read capture")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.continuations < 0:
        parser.error("--continuations must be non-negative")
    if args.generated_tokens <= 0:
        parser.error("--generated-tokens must be positive")
    if args.workload_index < 0:
        parser.error("--workload-index must be non-negative")
    if args.long_token_limit < 0:
        parser.error("--long-token-limit must be non-negative")
    workload_path = (args.workload_file.expanduser().resolve() if args.workload_file is not None
                     else BASE / "workloads.json")
    if not workload_path.is_file():
        parser.error(f"workload file does not exist: {workload_path}")
    if args.capture_moe_rows <= 0 or args.capture_moe_rows > 4096:
        parser.error("--capture-moe-rows must be between 1 and 4096")
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
    short_occurrences = 2 if args.sequence == "short-long-short" else 3
    short_request_count = short_occurrences + args.continuations
    if args.dump_gdn_occurrence is not None and args.dump_gdn_occurrence > short_request_count:
        parser.error("dump occurrence exceeds the number of 512-token requests; add continuations or lower the occurrence")
    if (args.capture_cpu_output_layer is None) != (args.capture_cpu_output_dispatch is None):
        parser.error("CPU output capture requires both --capture-cpu-output-layer and --capture-cpu-output-dispatch")
    if args.capture_cpu_output_layer is not None and (
            args.capture_cpu_output_layer < 0 or args.capture_cpu_output_dispatch < 0 or
            args.capture_cpu_output_position < 0):
        parser.error("CPU output capture layer and dispatch must be non-negative")
    if args.capture_verify_moe_layer is not None and args.capture_verify_moe_layer < 0:
        parser.error("verifier MoE capture layer must be non-negative")
    try:
        verify_moe_positions = [int(value) for value in args.verify_moe_positions.split(",")]
    except ValueError:
        parser.error("--verify-moe-positions must be comma-separated non-negative integers")
    if not verify_moe_positions or any(value < 0 for value in verify_moe_positions) or \
            verify_moe_positions != sorted(set(verify_moe_positions)):
        parser.error("--verify-moe-positions must be strictly increasing non-negative integers")
    if args.capture_verify_gdn_layer is not None and args.capture_verify_gdn_layer < 0:
        parser.error("verifier GDN capture layer must be non-negative")
    try:
        verify_gdn_positions = [int(value) for value in args.verify_gdn_positions.split(",")]
    except ValueError:
        parser.error("--verify-gdn-positions must be comma-separated non-negative integers")
    if not verify_gdn_positions or any(value < 0 for value in verify_gdn_positions) or \
            verify_gdn_positions != sorted(set(verify_gdn_positions)):
        parser.error("--verify-gdn-positions must be strictly increasing non-negative integers")
    if args.capture_verify_gdn_state_layer is not None and args.capture_verify_gdn_state_layer < 0:
        parser.error("verifier GDN state capture layer must be non-negative")
    if args.capture_boundary_layer is not None and args.capture_boundary_layer < 0:
        parser.error("residual-boundary capture layer must be non-negative")
    if args.boundary_position < 0:
        parser.error("residual-boundary capture position must be non-negative")
    if (args.capture_gr_read_layer is None) != (args.gr_read_position is None) or \
            (args.capture_gr_read_layer is None) != (args.gr_read_output is None):
        parser.error("fused GR-read capture requires layer, position, and output path together")
    if args.capture_gr_read_layer is not None and (
            args.capture_gr_read_layer < 0 or args.capture_gr_read_layer >= 48 or args.gr_read_position < 0):
        parser.error("fused GR-read layer must be in [0, 47] and position non-negative")
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
    capture_all_gdn_layers = args.capture_gdn_commit_state_layer == "all"
    try:
        if args.capture_gdn_commit_state_layer is not None and not capture_all_gdn_layers:
            args.capture_gdn_commit_state_layer = int(args.capture_gdn_commit_state_layer)
    except ValueError:
        parser.error("GDN commit layer must be a non-negative integer or 'all'")
    if args.capture_gdn_commit_state_layer is not None and (
            (not capture_all_gdn_layers and args.capture_gdn_commit_state_layer < 0) or not gdn_commit_positions or
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
    if args.prompt_cache is not None:
        if args.prompt_cache < 0:
            parser.error("--prompt-cache must be non-negative")
        replace_option(argv, "--prompt-cache", args.prompt_cache)
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
    workload_set = json.loads(workload_path.read_text())
    workload_rows = workload_set.get("workloads", [])
    if args.workload_index >= len(workload_rows):
        parser.error(f"workload index {args.workload_index} is outside {len(workload_rows)} entries")
    workload = workload_rows[args.workload_index]
    encoded_long_ids = tokenizer.encode(template.render(workload["messages"], enable_thinking=False), parse_special=True)
    long_ids = encoded_long_ids[-args.long_token_limit:] if args.long_token_limit else encoded_long_ids
    if len(long_ids) < 512:
        parser.error(f"selected workload encodes to {len(long_ids)} tokens; at least 512 are required")
    short_ids = long_ids[-512:]
    long_name = f"long-{len(long_ids)}"
    short_name = "short-512"
    if args.sequence == "short-long-short":
        prompts = [(short_name, short_ids), (long_name, long_ids),
                   ("short-512-recovery", short_ids)]
    else:
        prompts = [("short-512", short_ids), ("short-512-intermediate", short_ids),
                   ("short-512-recovery", short_ids)]
    prompts.extend((f"short-512-continuation-{index + 1}", long_ids[-512:])
                   for index in range(args.continuations))

    log = args.output / "service.log"
    env = child_env(cfg)
    capture_path = args.output / ("all-layer-position511.jsonl" if capture_moe_positions == [511]
                                  else "all-layer-selected-positions.jsonl")
    env.update({
        "STRATA_STATE_HASH": "1", "STRATA_STATE_HASH_GDN": "1",
        "STRATA_STATE_HASH_QSA_LAYERS": "1",
        "STRATA_ACCEPTED_PREFIX_TRACE": "1", "STRATA_INTEGRATION_TRACE": "1",
        "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_CAPTURE_MOE_LAYER": "-1",
        "STRATA_CAPTURE_MOE_ROWS": str(args.capture_moe_rows),
        "STRATA_CAPTURE_MOE_START_ROW": "0",
        "STRATA_CAPTURE_MOE_POSITIONS": ",".join(map(str, capture_moe_positions)),
        "STRATA_CAPTURE_MOE_PATH": str(capture_path.resolve()),
        "STRATA_VERIFY_ADAPT_SWAPS": "1",
        "STRATA_NATIVE_CPU_Q8_1_DOT": args.native_cpu_q8_1_dot,
    })
    if args.native_cpu_q8_1_reciprocal_silu_layer is not None:
        if args.native_cpu_q8_1_reciprocal_silu_layer < 0:
            raise ValueError("--native-cpu-q8-1-reciprocal-silu-layer must be non-negative")
        env["STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER"] = str(
            args.native_cpu_q8_1_reciprocal_silu_layer)
    if args.native_cpu_q8_1_reciprocal_silu_expert is not None:
        if args.native_cpu_q8_1_reciprocal_silu_layer is None:
            raise ValueError("native CPU Q8_1 reciprocal-SiLU expert requires a selected layer")
        if args.native_cpu_q8_1_reciprocal_silu_expert < 0:
            raise ValueError("native CPU Q8_1 reciprocal-SiLU expert must be non-negative")
        env["STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT"] = str(
            args.native_cpu_q8_1_reciprocal_silu_expert)
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
            "STRATA_VERIFY_DUMP_MOE_PARTS_LAYER": str(args.capture_verify_moe_layer),
            "STRATA_VERIFY_DUMP_MOE_PARTS_PATH": str((args.output / "verify-moe-parts.bin").resolve()),
            "STRATA_VERIFY_DUMP_MOE_OUTPUT_LAYER": str(args.capture_verify_moe_layer),
            "STRATA_VERIFY_DUMP_MOE_OUTPUT_PATH": str((args.output / "verify-moe-output.bin").resolve()),
            "STRATA_VERIFY_DUMP_MOE_INPUT_LAYER": "all" if args.verify_moe_input_layers == "all"
                                                     else str(args.capture_verify_moe_layer),
            "STRATA_VERIFY_DUMP_MOE_INPUT_PATH": str((args.output / "verify-moe-input.bin").resolve()),
        })
        for kind in ("ROUTE", "PARTS", "OUTPUT", "INPUT"):
            if verify_moe_positions == [511]:
                env[f"STRATA_VERIFY_DUMP_MOE_{kind}_POSITION"] = "511"
            else:
                env[f"STRATA_VERIFY_DUMP_MOE_{kind}_POSITIONS"] = ",".join(map(str, verify_moe_positions))
    if args.capture_boundary_layer is not None:
        env.update({
            "STRATA_VERIFY_DUMP_BOUNDARY_LAYER": str(args.capture_boundary_layer),
            "STRATA_VERIFY_DUMP_BOUNDARY_PATH": str((args.output / "verify-boundary.bin").resolve()),
            "STRATA_VERIFY_DUMP_BOUNDARY_POSITION": str(args.boundary_position),
        })
    gr_read_output = None
    if args.gr_read_output is not None:
        gr_read_output = args.gr_read_output.expanduser().resolve()
        if gr_read_output.exists():
            parser.error(f"fused GR-read output already exists: {gr_read_output}")
        gr_read_output.parent.mkdir(parents=True, exist_ok=True)
        env.update({
            "STRATA_VERIFY_DUMP_GR_READ_LAYER": str(args.capture_gr_read_layer),
            "STRATA_VERIFY_DUMP_GR_READ_POSITION": str(args.gr_read_position),
            "STRATA_VERIFY_DUMP_GR_READ_PATH": str(gr_read_output),
        })
    if args.capture_verify_gdn_layer is not None:
        env.update({
            "STRATA_VERIFY_DUMP_GDN_LAYER": str(args.capture_verify_gdn_layer),
            "STRATA_VERIFY_DUMP_GDN_PATH": str((args.output / "verify-gdn.bin").resolve()),
        })
        if verify_gdn_positions == [511]:
            env["STRATA_VERIFY_DUMP_GDN_POSITION"] = "511"
        else:
            env["STRATA_VERIFY_DUMP_GDN_POSITIONS"] = ",".join(map(str, verify_gdn_positions))
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
            ids = [int(token) for token in engine.generate(
                prompt, args.generated_tokens, {"temperature": 0}, threading.Event())
                   if token is not None]
            hashes = parse_hashes(log)
            if args.prompt_cache == 0:
                if hashes:
                    raise RuntimeError("unexpected persistent-state hashes with prompt cache disabled")
                state = None  # The engine intentionally emits session hashes only with prompt caching enabled.
            else:
                if len(hashes) != len(requests) + 1:
                    raise RuntimeError(f"expected {len(requests) + 1} state records, found {len(hashes)}")
                state = hashes[-1]
            requests.append({"name": name, "prompt_tokens": len(prompt),
                             "generated_tokens_requested": args.generated_tokens, "ids": ids,
                             "state": state})
            (args.output / "requests.json").write_text(json.dumps({"requests": requests}, indent=2) + "\n")
    finally:
        engine.close()

    gdn_commit_capture = None
    if gdn_commit_state_output is not None:
        header = struct.Struct("<8sIiqQQii")
        raw = gdn_commit_state_output.read_bytes()
        offset = 0
        observed = {}
        captured_layers = set()
        while offset < len(raw):
            if len(raw) - offset < header.size:
                raise RuntimeError("truncated committed GDN state header")
            magic, version, layer, position, recurrent, total, token, slot = header.unpack_from(raw, offset)
            offset += header.size
            if magic != b"STGCMT1\0" or version != 1 or (
                    not capture_all_gdn_layers and layer != args.capture_gdn_commit_state_layer):
                raise RuntimeError("invalid committed GDN state record")
            captured_layers.add(layer)
            if total < recurrent or len(raw) - offset < total * 4:
                raise RuntimeError("truncated committed GDN state payload")
            offset += total * 4
            observed[position] = observed.get(position, 0) + 1
        if not observed or any(count < 2 for count in observed.values()):
            raise RuntimeError(f"committed GDN positions were not captured in both short requests: {observed}")
        gdn_commit_capture = {
            "layer": args.capture_gdn_commit_state_layer,
            "captured_layers": sorted(captured_layers),
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
        expected = {position: short_request_count for position in state_positions}
        if observed != expected:
            raise RuntimeError(f"verifier GDN state positions have unexpected request counts: {observed}; expected {expected}")

    captured = [json.loads(line) for line in capture_path.read_text().splitlines()]
    if not captured or captured[0].get("format") != "strata-moe-dispatch-v3":
        raise RuntimeError("missing current all-layer dispatch capture")
    rows = captured[1:]
    for row in rows:
        expected_activation_valid = any(owner < 0 for owner in row["route_kind"])
        if "activation_valid" in row and row["activation_valid"] != expected_activation_valid:
            raise RuntimeError("CPU-pool activation validity does not match row ownership")
        activation = row.get("activation", [])
        if expected_activation_valid:
            if len(activation) != captured[0].get("n_embd") or not all(math.isfinite(x) for x in activation):
                raise RuntimeError("valid CPU-pool activation has an invalid width or non-finite value")
        elif "activation_valid" in row and activation:
            raise RuntimeError("CPU-pool trace serialized an activation without a CPU-owned expert")
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
                       and row.get("position") == args.capture_cpu_output_position]
        if not target_rows:
            raise RuntimeError(
                "CPU expert output capture missed the selected layer/dispatch at "
                f"position {args.capture_cpu_output_position}")
        cpu_output_capture = {
            "layer": args.capture_cpu_output_layer,
            "dispatch": args.capture_cpu_output_dispatch,
            "rows": len(output_rows),
            "target_position_rows": len(target_rows),
            "position": args.capture_cpu_output_position,
        }
    verify_moe_capture = None
    if args.capture_verify_moe_layer is not None:
        route_path = args.output / "verify-moe-routes.jsonl"
        input_path = args.output / "verify-moe-input.bin"
        parts_path = args.output / "verify-moe-parts.bin"
        output_path = args.output / "verify-moe-output.bin"
        if not route_path.is_file() or not input_path.is_file() or not parts_path.is_file() or not output_path.is_file():
            raise RuntimeError("requested verifier MoE input/route/parts/output capture was not written")
        route_records = [json.loads(line) for line in route_path.read_text().splitlines()]
        selected_routes = [row for row in route_records[1:]
                           if row.get("layer") == args.capture_verify_moe_layer
                           and row.get("position") in verify_moe_positions]
        counts = {position: sum(row.get("position") == position for row in selected_routes)
                  for position in verify_moe_positions}
        if counts != {position: short_request_count for position in verify_moe_positions}:
            raise RuntimeError(f"expected {short_request_count} short-request verifier route rows at selected positions; got {counts}")
        input_header = struct.Struct("<8sIIIIQq8i")
        raw_input = input_path.read_bytes()
        input_counts = {}
        expected_input_layers = set(range(48)) if args.verify_moe_input_layers == "all" else {args.capture_verify_moe_layer}
        offset = 0
        while offset < len(raw_input):
            if len(raw_input) - offset < input_header.size:
                raise RuntimeError("truncated verifier MoE input diagnostic header")
            magic, version, layer, input_rows, reserved, n_embd, pos0, *tokens = input_header.unpack_from(raw_input, offset)
            offset += input_header.size
            if magic != b"STMOINP1" or version != 1 or layer not in expected_input_layers or \
                    reserved != 0 or not 0 < input_rows <= 8 or n_embd != 2560:
                raise RuntimeError("invalid verifier MoE input diagnostic header")
            nbytes = input_rows * n_embd * 4
            if len(raw_input) - offset < nbytes:
                raise RuntimeError("truncated verifier MoE input diagnostic payload")
            if any(not math.isfinite(value[0]) for value in struct.iter_unpack("<f", raw_input[offset:offset + nbytes])):
                raise RuntimeError(f"non-finite verifier MoE input at layer {layer}, position {pos0}")
            offset += nbytes
            for position in verify_moe_positions:
                if pos0 <= position < pos0 + input_rows:
                    key = (layer, position)
                    input_counts[key] = input_counts.get(key, 0) + 1
        expected_input_counts = {(layer, position): short_request_count
                                 for layer in expected_input_layers for position in verify_moe_positions}
        if input_counts != expected_input_counts:
            raise RuntimeError(f"unexpected verifier input layer/position coverage: {input_counts}; expected {expected_input_counts}")
        verify_moe_capture = {
            "layer": args.capture_verify_moe_layer,
            "positions": verify_moe_positions,
            "route_rows": len(selected_routes),
            "input_layers": "all" if args.verify_moe_input_layers == "all" else [args.capture_verify_moe_layer],
            "input_bytes": len(raw_input),
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
            "positions": verify_gdn_positions,
            "bytes": gdn_path.stat().st_size,
        }
    verify_gdn_state_capture = None
    if gdn_state_output is not None:
        if not gdn_state_output.is_file():
            raise RuntimeError("requested pre/post GDN state capture was not written")
        verify_gdn_state_capture = {
            "layer": args.capture_verify_gdn_state_layer,
            "requested_positions": state_positions,
            "observed_records_per_position": observed,
            "path": str(gdn_state_output),
            "bytes": gdn_state_output.stat().st_size,
        }
    verify_boundary_capture = None
    if args.capture_boundary_layer is not None:
        boundary_path = args.output / "verify-boundary.bin"
        header = struct.Struct("<8sIIQQQii")
        raw_boundary = boundary_path.read_bytes() if boundary_path.is_file() else b""
        records = 0
        expected_payload = (2 * (4 * 2560 + 2560 + 4) + 2 * 4 * 2560) * 4
        offset = 0
        while offset < len(raw_boundary):
            if len(raw_boundary) - offset < header.size:
                raise RuntimeError("truncated verifier boundary diagnostic header")
            magic, version, layer, position, n_embd, hc, token, reserved = header.unpack_from(raw_boundary, offset)
            offset += header.size
            if magic != b"STBNDY1\0" or version != 1 or layer != args.capture_boundary_layer or \
                    position != args.boundary_position or n_embd != 2560 or hc != 4 or reserved != 0:
                raise RuntimeError("invalid verifier boundary diagnostic header")
            if len(raw_boundary) - offset < expected_payload:
                raise RuntimeError("truncated verifier boundary diagnostic payload")
            if any(not math.isfinite(value[0]) for value in struct.iter_unpack(
                    "<f", raw_boundary[offset:offset + expected_payload])):
                raise RuntimeError(f"non-finite verifier boundary values at position {position}")
            offset += expected_payload
            records += 1
        if records != short_request_count:
            raise RuntimeError(f"expected {short_request_count} verifier boundary records, got {records}")
        verify_boundary_capture = {
            "layer": args.capture_boundary_layer,
            "next_layer": args.capture_boundary_layer + 1,
            "position": args.boundary_position,
            "records": records,
            "bytes": len(raw_boundary),
            "path": str(boundary_path),
        }
    verify_gr_read_capture = None
    if gr_read_output is not None:
        header = struct.Struct("<8sIIqiiQQQ")
        raw_gr = gr_read_output.read_bytes() if gr_read_output.is_file() else b""
        offset = 0
        tokens = []
        while offset < len(raw_gr):
            if len(raw_gr) - offset < header.size:
                raise RuntimeError("truncated fused GR-read diagnostic header")
            magic, version, layer, position, token, reserved, n_embd, hc, hc_lr = header.unpack_from(raw_gr, offset)
            offset += header.size
            if magic != b"STGRRD1\0" or version != 1 or layer != args.capture_gr_read_layer or \
                    position != args.gr_read_position or reserved != 0 or n_embd != 2560 or hc != 4:
                raise RuntimeError("invalid fused GR-read diagnostic header")
            floats = hc * n_embd + n_embd + 2 * hc + hc_lr
            payload_bytes = floats * 4
            if len(raw_gr) - offset < payload_bytes:
                raise RuntimeError("truncated fused GR-read diagnostic payload")
            if any(not math.isfinite(value[0]) for value in struct.iter_unpack(
                    "<f", raw_gr[offset:offset + payload_bytes])):
                raise RuntimeError("non-finite fused GR-read values")
            offset += payload_bytes
            tokens.append(token)
        expected_count = short_request_count if args.gr_read_position < 2048 else 0
        if len(tokens) != expected_count:
            raise RuntimeError(f"expected {expected_count} fused GR-read records, got {len(tokens)}")
        verify_gr_read_capture = {
            "layer": args.capture_gr_read_layer,
            "position": args.gr_read_position,
            "records": len(tokens),
            "tokens": tokens,
            "bytes": len(raw_gr),
            "path": str(gr_read_output),
        }
    route = {"rows": len(rows),
             "layers": sorted({row["layer"] for row in rows}),
             "positions": sorted({row["position"] for row in rows})}
    state_changes = None if requests[0]["state"] is None else [
        key for key in STATE_KEYS if requests[0]["state"][key] != requests[2]["state"][key]]
    results = {
        "adapt_every": args.adapt_every, "adapt_swaps": args.adapt_swaps,
        "prompt_cache": int(argv[argv.index("--prompt-cache") + 1]) if "--prompt-cache" in argv else None,
        "accepted_state_hashes_available": requests[0]["state"] is not None,
        "sequence": args.sequence,
        "prompt_workload_file": str(workload_path),
        "prompt_workload_file_sha256": hashlib.sha256(workload_path.read_bytes()).hexdigest(),
        "prompt_workload_index": args.workload_index,
        "prompt_workload_cell": workload.get("cell"),
        "prompt_encoded_source_tokens": len(encoded_long_ids),
        "prompt_long_tokens": len(long_ids),
        "prompt_long_token_limit": args.long_token_limit,
        "configured_spec": configured_spec, "spec_override": args.spec,
        "capture_moe_positions": capture_moe_positions,
        "capture_moe_rows": args.capture_moe_rows,
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
        "verify_boundary_capture": verify_boundary_capture,
        "verify_gr_read_capture": verify_gr_read_capture,
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
