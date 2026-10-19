#!/usr/bin/env python3
"""Capture generated rows while seven layer-2 experts change owners."""
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
from tools.integration.accepted_prefix_parity import STATE_KEYS as BASE_STATE_KEYS
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

STATE_KEYS = (*BASE_STATE_KEYS, "mtp", "stale")


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
    ap.add_argument("--arm", choices=("cpu_mirror", "gpu_layer2"), required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--dump-prefill-gdn", action="store_true",
                    help="retain the exact prompt-end GDN state bytes (diagnostic build only)")
    ap.add_argument("--device-layer", type=int, default=2,
                    help="verifier layer to capture on device (0-47; default: 1)")
    ap.add_argument("--output-layer", type=int, default=2,
                    help="MoE layer whose CPU-owned expert outputs to capture (0-47; default: 1)")
    ap.add_argument("--hash-qsa-layers", action="store_true",
                    help="log per-QSA-layer state fingerprints at each accepted prefix")
    ap.add_argument("--dump-moe-route-layer", type=int,
                    help="capture exact verifier device top-k IDs/weights for one layer (0-47)")
    ap.add_argument("--dump-moe-parts-layer", type=int,
                    help="capture verifier expert outputs before router-weighted combine (0-47)")
    a = ap.parse_args()
    if not 0 <= a.device_layer < 48:
        ap.error("--device-layer must be in [0, 47]")
    if not 0 <= a.output_layer < 48:
        ap.error("--output-layer must be in [0, 47]")
    if a.dump_moe_route_layer is not None and not 0 <= a.dump_moe_route_layer < 48:
        ap.error("--dump-moe-route-layer must be in [0, 47]")
    if a.dump_moe_parts_layer is not None and not 0 <= a.dump_moe_parts_layer < 48:
        ap.error("--dump-moe-parts-layer must be in [0, 47]")
    a.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((HERE / "config.json").read_text())
    argv = list(cfg["args"])
    replace_option(argv, "--adapt-every", 0)
    replace_option(argv, "--adapt-swaps", 0)
    replace_option(argv, "--prompt-cache", 0)
    replace_option(argv, "--expert-cache", 3007)
    profile = HERE / ("profile-control.bin" if a.arm == "cpu_mirror" else "profile-gpu-layer2.bin")
    replace_option(argv, "--expert-profile", profile)
    env = child_env(cfg)
    env.update({"STRATA_STATE_HASH": "1", "STRATA_STATE_HASH_GDN": "1",
                "STRATA_ACCEPTED_PREFIX_TRACE": "1", "STRATA_INTEGRATION_TRACE": "1",
                "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_VERIFY_ADAPT_SWAPS": "1",
                "STRATA_NATIVE_CPU_Q8_1_DOT": "iq2_s/iq4_nl@layer=2",
                "STRATA_CAPTURE_MOE_LAYER": "-1", "STRATA_CAPTURE_MOE_ROWS": "768",
                "STRATA_CAPTURE_MOE_START_ROW": "0",
                "STRATA_CAPTURE_MOE_PATH": str((a.output / "routes-all-layers.jsonl").resolve()),
                "STRATA_CAPTURE_MOE_OUTPUT_PATH": str((a.output / f"cpu-outputs-layer{a.output_layer}.jsonl").resolve()),
                "STRATA_CAPTURE_MOE_OUTPUT_LAYER": str(a.output_layer),
                "STRATA_VERIFY_DUMP_GDN_LAYER": str(a.device_layer),
                "STRATA_VERIFY_DUMP_GDN_PATH": str((a.output / "combined-moe.bin").resolve())})
    if a.dump_prefill_gdn:
        env["STRATA_PREFILL_DUMP_GDN"] = str((a.output / "prefill-gdn.bin").resolve())
    if a.hash_qsa_layers:
        env["STRATA_STATE_HASH_QSA_LAYERS"] = "1"
    if a.dump_moe_route_layer is not None:
        env["STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER"] = str(a.dump_moe_route_layer)
        env["STRATA_VERIFY_DUMP_MOE_ROUTE_PATH"] = str((a.output / "device-moe-routes.jsonl").resolve())
    if a.dump_moe_parts_layer is not None:
        env["STRATA_VERIFY_DUMP_MOE_PARTS_LAYER"] = str(a.dump_moe_parts_layer)
        env["STRATA_VERIFY_DUMP_MOE_PARTS_PATH"] = str((a.output / "device-moe-parts.bin").resolve())
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
    cpu_lines = (a.output / f"cpu-outputs-layer{a.output_layer}.jsonl").read_text().splitlines()
    if not cpu_lines or json.loads(cpu_lines[0]).get("format") != "strata-moe-cpu-output-v2":
        raise RuntimeError("missing CPU output capture")
    cpu_rows = [json.loads(line) for line in cpu_lines[1:]]
    if any(row.get("layer") != a.output_layer for row in cpu_rows):
        raise RuntimeError(f"CPU output capture included a row outside layer {a.output_layer}")
    prefill_dump = a.output / "prefill-gdn.bin"
    prefill_hash = hashlib.sha256(prefill_dump.read_bytes()).hexdigest() if prefill_dump.exists() else None
    (a.output / "requests.json").write_text(json.dumps({
        "arm": a.arm, "selector": env["STRATA_NATIVE_CPU_Q8_1_DOT"],
        "expert_cache_argument": 3007, "prompt_tokens": len(prompt), "prompt_sha256": hashlib.sha256(
            b"".join(int(x).to_bytes(4, "little", signed=True) for x in prompt)).hexdigest(),
        "completion_ids": ids, "state": hashes[-1], "accepted_prefix_records": len(hashes),
        "cpu_output_records": len(cpu_rows), "cpu_output_layer": a.output_layer,
        "captured_positions_per_layer": 16,
        "captured_layers": 48, "profile": str(profile),
        "profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
        "prefill_gdn_sha256": prefill_hash,
        "prefill_gdn_bytes": prefill_dump.stat().st_size if prefill_dump.exists() else 0}, indent=2) + "\n")
    print(f"{a.arm}: passed; route rows={len(route)}, layer-{a.output_layer} CPU outputs={len(cpu_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
