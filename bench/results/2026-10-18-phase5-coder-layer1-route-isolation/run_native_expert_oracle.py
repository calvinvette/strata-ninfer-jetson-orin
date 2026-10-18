#!/usr/bin/env python3
"""Compare captured Coder CPU expert rows with the float/GPU parity oracle."""
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "position-keyed-three-arm"
ORACLE = CAMPAIGN / "oracle"
ACTIVATION = ORACLE / "activation-position-511-token-271.f32"
MODEL = Path("/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf")
PARITY = ROOT / "build/integration/candidate/native_expert_parity"


def read_f32(path):
    data = Path(path).read_bytes()
    if len(data) % 4:
        raise ValueError(f"non-float32 file: {path}")
    return struct.unpack(f"<{len(data) // 4}f", data)


def metrics(a, b):
    if len(a) != len(b):
        raise ValueError("float vectors have different lengths")
    diffs = [abs(x - y) for x, y in zip(a, b)]
    return {
        "bitwise_equal": all(struct.pack("<f", x) == struct.pack("<f", y) for x, y in zip(a, b)),
        "different_values": sum(x != y for x, y in zip(a, b)),
        "values": len(a),
        "max_abs": max(diffs, default=0.0),
        "relative_l1": math.fsum(diffs) / max(math.fsum(abs(x) for x in a), 1e-30),
    }


route_file = CAMPAIGN / "cpu_default/result/layer1.jsonl"
route_rows = [json.loads(line) for line in route_file.read_text().splitlines()[1:]]
route = next(r for r in route_rows if r["dispatch"] == 1 and r["layer"] == 1 and r["row"] == 0)
if (route["position"], route["token_id"]) != (511, 271):
    raise RuntimeError("unexpected route row key")
activation_bytes = struct.pack(f"<{len(route['activation'])}f", *route["activation"])
if not ACTIVATION.exists():
    ACTIVATION.write_bytes(activation_bytes)
if ACTIVATION.read_bytes() != activation_bytes:
    raise RuntimeError("saved activation does not round-trip to the route capture")
experts = [route["ids"][i] for i, owner in enumerate(route["route_kind"]) if owner < 0]
if experts != [205, 101, 32, 11, 95, 18, 165]:
    raise RuntimeError(f"unexpected CPU-owned experts: {experts}")

service_outputs = {}
for arm in ("cpu_default", "cpu_mirror"):
    rows = [json.loads(line) for line in (CAMPAIGN / arm / "result/cpu-outputs.jsonl").read_text().splitlines()[1:]]
    service_outputs[arm] = {r["expert"]: tuple(r["output"]) for r in rows
                            if r["dispatch"] == 1 and r["layer"] == 1}
    if set(service_outputs[arm]) != set(experts):
        raise RuntimeError(f"{arm} CPU outputs do not match route misses")

binary_hash = hashlib.sha256(PARITY.read_bytes()).hexdigest()
summary = {
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "model_quantization": "IQ1_M",
    "parity_binary_sha256": binary_hash,
    "route_key": {"position": route["position"], "token_id": route["token_id"], "layer": route["layer"]},
    "expert_format": "IQ2_S gate/up, Q2_0 down",
    "activation_sha256": hashlib.sha256(ACTIVATION.read_bytes()).hexdigest(),
    "experts": {},
    "all_default_service_outputs_match_default_parity_cpu": False,
    "all_mirror_service_outputs_match_candidate_parity_cpu": False,
    "all_candidate_parity_cpu_outputs_match_gpu_bitwise": False,
    "all_checks_pass": False,
}

with tempfile.TemporaryDirectory(prefix="strata-route-oracle-") as work:
    tmp = Path(work)
    log_dir = ORACLE / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for expert in experts:
        record = {"expert": expert}
        for mode, env_flag, service_arm in (("default", None, "cpu_default"), ("q8_1", "1", "cpu_mirror")):
            out_dir = tmp / f"e{expert}-{mode}"
            out_dir.mkdir()
            env = os.environ.copy()
            if env_flag is None:
                env.pop("STRATA_NATIVE_CPU_Q8_1_DOT", None)
            else:
                env["STRATA_NATIVE_CPU_Q8_1_DOT"] = env_flag
            command = [str(PARITY), str(MODEL), "--expert", str(expert), "--activation-f32", str(ACTIVATION),
                       "--dump-f32-dir", str(out_dir), "1"]
            proc = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            log_path = log_dir / f"expert-{expert}-{mode}.txt"
            log_path.write_text(proc.stdout)
            if proc.returncode != 0 or "native_expert_parity: 0 failures" not in proc.stdout:
                raise RuntimeError(f"parity failed for expert {expert}/{mode}; see {log_path}")
            expected = read_f32(out_dir / f"layer-1-expert-{expert}-cpu-output.f32")
            ref = read_f32(out_dir / f"layer-1-expert-{expert}-float-output.f32")
            service = service_outputs[service_arm][expert]
            record[mode] = {
                "service_vs_parity_cpu": metrics(service, expected),
                "cpu_vs_float_reference": metrics(expected, ref),
                "cpu_relative_l1_vs_float_reference": metrics(expected, ref)["relative_l1"],
                "log": log_path.name,
            }
            if mode == "q8_1":
                gpu = read_f32(out_dir / f"layer-1-expert-{expert}-gpu-output.f32")
                record[mode]["candidate_cpu_vs_gpu"] = metrics(expected, gpu)
                if not record[mode]["candidate_cpu_vs_gpu"]["bitwise_equal"]:
                    raise RuntimeError(f"Q8_1 candidate/GPU output mismatch for expert {expert}")
            shutil.rmtree(out_dir)
        summary["experts"][str(expert)] = record

summary["all_default_service_outputs_match_default_parity_cpu"] = all(
    x["default"]["service_vs_parity_cpu"]["bitwise_equal"] for x in summary["experts"].values())
summary["all_mirror_service_outputs_match_candidate_parity_cpu"] = all(
    x["q8_1"]["service_vs_parity_cpu"]["bitwise_equal"] for x in summary["experts"].values())
summary["all_candidate_parity_cpu_outputs_match_gpu_bitwise"] = all(
    x["q8_1"]["candidate_cpu_vs_gpu"]["bitwise_equal"] for x in summary["experts"].values())
summary["all_checks_pass"] = all(summary[k] for k in (
    "all_default_service_outputs_match_default_parity_cpu",
    "all_mirror_service_outputs_match_candidate_parity_cpu",
    "all_candidate_parity_cpu_outputs_match_gpu_bitwise"))
out = ORACLE / "analysis.json"
out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
if not summary["all_checks_pass"]:
    raise SystemExit(1)
