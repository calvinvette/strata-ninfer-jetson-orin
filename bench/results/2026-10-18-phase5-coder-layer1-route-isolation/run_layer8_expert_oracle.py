#!/usr/bin/env python3
"""Check captured layer-8 CPU expert rows against the independent native oracle."""
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "layer8-output-pair"
ORACLE = CAMPAIGN / "oracle"
ACTIVATION = ORACLE / "activation-position-511-token-271.f32"
MODEL = Path("/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf")
PARITY = ROOT / "build/integration/candidate/native_expert_parity"


def read_f32(path):
    raw = Path(path).read_bytes()
    if len(raw) % 4:
        raise ValueError(f"not a float32 file: {path}")
    return struct.unpack(f"<{len(raw) // 4}f", raw)


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


ORACLE.mkdir(parents=True, exist_ok=True)
route_rows = {}
for arm in ("cpu_mirror", "gpu_layer1"):
    rows = [json.loads(line) for line in (CAMPAIGN / arm / "result/routes-all-layers.jsonl").read_text().splitlines()[1:]]
    route_rows[arm] = next(r for r in rows if r["layer"] == 8 and r["position"] == 511)
left, right = route_rows["cpu_mirror"], route_rows["gpu_layer1"]
if (left["token_id"], left["activation"], left["ids"], left["route_kind"]) != \
   (right["token_id"], right["activation"], right["ids"], right["route_kind"]):
    raise RuntimeError("layer-8 activation, route IDs, or owners do not match at position 511")
if left["token_id"] != 271:
    raise RuntimeError(f"unexpected layer-8 position-511 token id {left['token_id']}")
activation = struct.pack(f"<{len(left['activation'])}f", *left["activation"])
if len(left["activation"]) != 2560:
    raise RuntimeError("expected the Coder's 2,560-wide layer-8 activation")
ACTIVATION.write_bytes(activation)

experts = [expert for expert, owner in zip(left["ids"], left["route_kind"]) if owner < 0]
outputs = {}
for arm in ("cpu_mirror", "gpu_layer1"):
    lines = (CAMPAIGN / arm / "result/cpu-outputs-layer8.jsonl").read_text().splitlines()
    captured = [json.loads(line) for line in lines[1:]]
    outputs[arm] = {r["expert"]: tuple(r["output"]) for r in captured
                    if r["position"] == 511 and r["token_id"] == 271 and r["layer"] == 8}
    if set(outputs[arm]) != set(experts):
        raise RuntimeError(f"{arm} layer-8 service outputs do not match CPU-owned experts")

result = {
    "schema": 1,
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "model_quantization": "IQ1_M",
    "layer": 8,
    "route_key": {"position": 511, "token_id": 271},
    "activation_sha256": hashlib.sha256(activation).hexdigest(),
    "expert_formats": {},
    "experts": {},
    "all_checks_pass": False,
}

with tempfile.TemporaryDirectory(prefix="strata-layer8-oracle-") as work:
    tmp = Path(work)
    for expert in experts:
        item = {}
        for mode, service_arm, q8_1 in (("default", "gpu_layer1", False),
                                        ("q8_1", "cpu_mirror", True)):
            out_dir = tmp / f"e{expert}-{mode}"
            out_dir.mkdir()
            env = os.environ.copy()
            if q8_1:
                env["STRATA_NATIVE_CPU_Q8_1_DOT"] = "1"
            else:
                env.pop("STRATA_NATIVE_CPU_Q8_1_DOT", None)
            command = [str(PARITY), str(MODEL), "--expert", str(expert),
                       "--activation-f32", str(ACTIVATION), "--dump-f32-dir", str(out_dir), "8"]
            proc = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            log = ORACLE / "runs" / f"layer8-expert-{expert}-{mode}.txt"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(proc.stdout)
            if proc.returncode != 0 or "native_expert_parity: 0 failures" not in proc.stdout:
                raise RuntimeError(f"independent parity failed for expert {expert}/{mode}; see {log}")
            format_line = next((line.strip() for line in proc.stdout.splitlines()
                                if line.startswith("layer 8 expert ")), None)
            if format_line is None:
                raise RuntimeError(f"oracle omitted layer-8 format summary for expert {expert}")
            format_match = re.search(r"^layer 8 expert \d+ (\S+)\s+/(\S+)", format_line)
            if format_match is None:
                raise RuntimeError(f"could not parse expert format from {format_line!r}")
            format_key = f"{format_match.group(1)}/{format_match.group(2)}"
            prior_format = result["expert_formats"].setdefault(str(expert), format_key)
            if prior_format != format_key:
                raise RuntimeError(f"oracle format disagrees across arithmetic modes for expert {expert}")
            prefix = f"layer-8-expert-{expert}"
            cpu = read_f32(out_dir / f"{prefix}-cpu-output.f32")
            float_ref = read_f32(out_dir / f"{prefix}-float-output.f32")
            item[mode] = {
                "service_vs_parity_cpu": metrics(outputs[service_arm][expert], cpu),
                "cpu_vs_float_reference": metrics(cpu, float_ref),
                "log": log.name,
            }
            if q8_1:
                gpu = read_f32(out_dir / f"{prefix}-gpu-output.f32")
                item[mode]["candidate_cpu_vs_gpu"] = metrics(cpu, gpu)
                if not item[mode]["candidate_cpu_vs_gpu"]["bitwise_equal"]:
                    raise RuntimeError(f"Q8_1 CPU/CUDA mismatch for expert {expert}")
            shutil.rmtree(out_dir)
        result["experts"][str(expert)] = item

result["all_default_service_outputs_match_default_parity_cpu"] = all(
    x["default"]["service_vs_parity_cpu"]["bitwise_equal"] for x in result["experts"].values())
result["all_mirror_service_outputs_match_candidate_parity_cpu"] = all(
    x["q8_1"]["service_vs_parity_cpu"]["bitwise_equal"] for x in result["experts"].values())
result["all_candidate_parity_cpu_outputs_match_gpu_bitwise"] = all(
    x["q8_1"]["candidate_cpu_vs_gpu"]["bitwise_equal"] for x in result["experts"].values())
result["all_checks_pass"] = all(result[k] for k in (
    "all_default_service_outputs_match_default_parity_cpu",
    "all_mirror_service_outputs_match_candidate_parity_cpu",
    "all_candidate_parity_cpu_outputs_match_gpu_bitwise"))
output = ORACLE / "analysis-layer8.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if not result["all_checks_pass"]:
    raise SystemExit(1)
