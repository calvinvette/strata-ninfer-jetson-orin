#!/usr/bin/env python3
"""Compare CPU expert rows with CUDA for the first matching pre-divergence input."""
import argparse
import json
import os
import struct
import subprocess
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--layer", type=int, default=1)
    ap.add_argument("--dispatch", type=int, default=1393)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("choose a new output directory")
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parents[3]
    capture = root / "bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/pair1/default/result/layer1.jsonl"
    model = Path("/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf")
    binary = root / "build/integration/candidate/native_expert_parity"
    matches = []
    for line in capture.read_text().splitlines()[1:]:
        row = json.loads(line)
        if row["dispatch"] == args.dispatch and row["layer"] == args.layer:
            matches.append(row)
    if len(matches) != 1:
        raise RuntimeError(f"expected one layer {args.layer} dispatch {args.dispatch}, found {len(matches)}")
    row = matches[0]
    activation = args.output / "activation.f32"
    activation.write_bytes(struct.pack("<%sf" % len(row["activation"]), *row["activation"]))
    experts = [expert for expert, owner in zip(row["ids"], row["route_kind"]) if owner == -1]
    manifest = {"schema": 1, "layer": args.layer, "dispatch": args.dispatch,
                "cpu_owned_experts": experts, "activation_sha256": __import__("hashlib").sha256(activation.read_bytes()).hexdigest(),
                "binary_sha256": __import__("hashlib").sha256(binary.read_bytes()).hexdigest(),
                "started_wall_time_s": time.time(), "runs": []}
    env_base = dict(os.environ)
    for expert in experts:
        for route in ("default", "cuda_mirror"):
            name = f"expert-{expert}-{route}"
            env = dict(env_base)
            env.pop("STRATA_NATIVE_CPU_Q8_1_DOT", None)
            if route == "cuda_mirror":
                env["STRATA_NATIVE_CPU_Q8_1_DOT"] = "1"
            cmd = [str(binary), str(model), "--expert", str(expert),
                   "--activation-f32", str(activation), str(args.layer)]
            result = subprocess.run(cmd, cwd=root, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (args.output / f"{name}.txt").write_text(result.stdout)
            manifest["runs"].append({"expert": expert, "route": route,
                                     "returncode": result.returncode, "command": cmd,
                                     "stdout": f"{name}.txt"})
            (args.output / "results.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"{name}: exit {result.returncode}", flush=True)
    manifest["finished_wall_time_s"] = time.time()
    (args.output / "results.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return int(any(run["returncode"] != 0 for run in manifest["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
