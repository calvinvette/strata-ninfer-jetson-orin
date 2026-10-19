#!/usr/bin/env python3
"""Compare actual layer-25 CPU expert outputs at the same Coder input row."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def f32_bytes(values):
    return b"".join(struct.pack("<f", float(x)) for x in values)


def summarize(a, b):
    aa = [float(x) for x in a]
    bb = [float(x) for x in b]
    delta = [y - x for x, y in zip(aa, bb)]
    return {
        "values": len(aa),
        "different_values": sum(x != y for x, y in zip(aa, bb)),
        "max_abs_diff": max((abs(x) for x in delta), default=0.0),
        "relative_l2": math.sqrt(math.fsum(x * x for x in delta) / math.fsum(x * x for x in aa)) if any(aa) else None,
        "initial_f32_sha256": hashlib.sha256(f32_bytes(aa)).hexdigest(),
        "recovery_f32_sha256": hashlib.sha256(f32_bytes(bb)).hexdigest(),
    }


def capture(run_dir, dispatch):
    route_rows = read_jsonl(run_dir / "all-layer-position511.jsonl")[1:]
    matches = [row for row in route_rows if row["layer"] == 25 and row["position"] == 511
               and row["dispatch"] == dispatch]
    if len(matches) != 1:
        raise ValueError(f"expected one layer-25 route row for dispatch {dispatch}, got {len(matches)}")
    route = matches[0]
    outputs = read_jsonl(run_dir / "cpu-moe-outputs.jsonl")[1:]
    outputs = [row for row in outputs if row["layer"] == 25 and row["dispatch"] == dispatch
               and row["position"] == 511]
    by_expert = {row["expert"]: row for row in outputs}
    if len(by_expert) != len(outputs):
        raise ValueError("duplicate CPU expert output rows")
    expected = {expert for expert, owner in zip(route["ids"], route["route_kind"]) if owner < 0}
    if set(by_expert) != expected:
        raise ValueError(f"CPU output experts {sorted(by_expert)} do not match routed CPU experts {sorted(expected)}")
    return route, by_expert


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--initial", type=Path, required=True, help="initial run directory")
    p.add_argument("--recovery", type=Path, required=True, help="recovery run directory")
    p.add_argument("--initial-dispatch", type=int, default=169)
    p.add_argument("--recovery-dispatch", type=int, default=1993)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    initial_summary = json.loads((args.initial / "analysis.json").read_text())
    recovery_summary = json.loads((args.recovery / "analysis.json").read_text())
    if initial_summary["binary_sha256"] != recovery_summary["binary_sha256"]:
        raise ValueError("initial and recovery captures used different service binaries")
    if initial_summary["prompt_sha256"] != recovery_summary["prompt_sha256"]:
        raise ValueError("initial and recovery captures used different prompt token sequences")
    initial_route, initial = capture(args.initial, args.initial_dispatch)
    recovery_route, recovery = capture(args.recovery, args.recovery_dispatch)
    route_identity = all(initial_route[key] == recovery_route[key]
                         for key in ("position", "token_id", "k", "ids", "route_kind", "activation"))
    if not route_identity:
        raise ValueError("the captured layer-25 route/input rows are not identical")
    per_expert = {str(expert): summarize(initial[expert]["output"], recovery[expert]["output"])
                  for expert in sorted(initial)}
    initial_all = [v for expert in sorted(initial) for v in initial[expert]["output"]]
    recovery_all = [v for expert in sorted(recovery) for v in recovery[expert]["output"]]
    result = {
        "scope": "single actual Coder IQ1_M service row; CPU-owned experts at layer 25",
        "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
        "binary_sha256": initial_summary["binary_sha256"],
        "short_prompt_sha256": initial_summary["prompt_sha256"]["short"],
        "position": 511,
        "token_id": initial_route["token_id"],
        "initial_dispatch": args.initial_dispatch,
        "recovery_dispatch": args.recovery_dispatch,
        "route_inputs_ids_and_owners_identical": route_identity,
        "cpu_experts": sorted(initial),
        "per_expert": per_expert,
        "combined_cpu_rows": summarize(initial_all, recovery_all),
        "limits": ["CPU expert rows only; GPU expert rows, router weights, shared expert and full layer output were not captured"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
