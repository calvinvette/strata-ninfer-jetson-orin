#!/usr/bin/env python3
"""Review same-activation layer-2 CPU/CUDA expert parity captures."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ROUTE = json.loads((HERE / "route.json").read_text())
EXPECTED = ROUTE["cpu_owned_experts"]
SOURCE_ROUTE = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/all-16-positions-three-arm-wildcard/cpu_default/result/routes-all-layers.jsonl"
PATTERN = re.compile(
    r"layer 2 expert (\d+) (\w+)\s*/(\w+)\s+blob\s+(\d+)\s+"
    r"cpu rel ([0-9.eE+-]+)\s+gpu rel ([0-9.eE+-]+)\s+"
    r"cpu-gpu ([0-9.eE+-]+) \((\d+)/(\d+) words differ\)\s+(\w+)"
)

records = []
for expert in EXPECTED:
    dirs = sorted(HERE.glob(f"supervisor-e{expert}-*"))
    passing = [p for p in dirs if (p / "result.json").exists()
               and json.loads((p / "result.json").read_text()).get("status") == "pass"]
    if len(passing) != 1:
        raise SystemExit(f"expert {expert}: expected one passing supervisor, found {len(passing)}")
    sup = passing[0]
    stdout = (sup / "stdout.txt").read_text()
    match = PATTERN.search(stdout)
    if not match:
        raise SystemExit(f"expert {expert}: no layer-2 parity summary in {sup}/stdout.txt")
    got_expert, gu, down, blob, cpu, gpu, delta, diff, count, status = match.groups()
    if int(got_expert) != expert or status != "ok" or int(diff) != int(count) or int(count) != 7680:
        raise SystemExit(f"expert {expert}: parity summary did not meet expected shape/status")
    result = json.loads((sup / "result.json").read_text())
    samples = [json.loads(line) for line in (sup / "memory.jsonl").read_text().splitlines() if line]
    events = {key: 0 for key in ("low", "high", "max", "oom", "oom_kill")}
    for sample in samples:
        for cg in sample.get("cgroups", []):
            for key in events:
                events[key] = max(events[key], int(cg.get("memory_events", {}).get(key, 0)))
    if result.get("status") != "pass" or result.get("returncode") != 0 or any(events.values()):
        raise SystemExit(f"expert {expert}: supervision or cgroup event check failed")
    records.append({
        "expert": expert, "gate_up_type": gu, "down_type": down,
        "blob_bytes": int(blob), "cpu_relative_l1_vs_fp64_reference": float(cpu),
        "cuda_relative_l1_vs_fp64_reference": float(gpu),
        "cpu_cuda_relative_l1": float(delta), "cpu_cuda_differing_f32_words": int(diff),
        "cpu_cuda_total_f32_words": int(count), "oracle_status": status,
        "supervisor_dir": str(sup.relative_to(ROOT)), "samples": len(samples),
        "minimum_host_gib": result["minimum_available_bytes"] / 1024**3,
        "minimum_admission_gib": result["minimum_admission_available_bytes"] / 1024**3,
        "cgroup_memory_events_max": events,
    })

if [r["expert"] for r in records] != EXPECTED:
    raise SystemExit("expert order does not match route")
if any(r["gate_up_type"] != "iq2_s" or r["down_type"] != "iq4_nl" for r in records):
    raise SystemExit("captured experts do not share the expected layer-2 codec pair")

source_rows = [json.loads(line) for line in SOURCE_ROUTE.read_text().splitlines()]
source_row = next((x for x in source_rows if x.get("position") == ROUTE["position"]
                   and x.get("token_id") == ROUTE["token_id"] and x.get("layer") == ROUTE["layer"]
                   and x.get("dispatch") == ROUTE["dispatch"]), None)
if source_row is None:
    raise SystemExit("route row is missing from retained all-layer source capture")
for key in ("position", "token_id", "dispatch", "layer", "ids", "route_kind"):
    if source_row[key] != ROUTE[key]:
        raise SystemExit(f"route identity mismatch for {key}")
source_activation = __import__("struct").pack(f"<{len(source_row['activation'])}f", *source_row["activation"])
activation_path = HERE / "activation-position-511-token-271-layer-2.f32"
if activation_path.read_bytes() != source_activation:
    raise SystemExit("activation file does not match the retained route source capture")

def quantile(values, q):
    ordered = sorted(values)
    i = (len(ordered) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (i - lo)

summary = {
    "schema": 1,
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "quantization": "IQ1_M",
    "route": {k: ROUTE[k] for k in ("position", "token_id", "dispatch", "layer", "cpu_owned_experts", "activation_sha256")},
    "source_route_capture": str(SOURCE_ROUTE.relative_to(ROOT)),
    "source_route_capture_sha256": hashlib.sha256(SOURCE_ROUTE.read_bytes()).hexdigest(),
    "activation_bytes": activation_path.stat().st_size,
    "activation_sha256_verified": hashlib.sha256(activation_path.read_bytes()).hexdigest() == ROUTE["activation_sha256"],
    "parity_binary_sha256": hashlib.sha256((ROOT / "build/integration/candidate/native_expert_parity").read_bytes()).hexdigest(),
    "all_cpu_owned_experts_tested": len(records) == len(EXPECTED) == 7,
    "interpretation": "For each captured expert, the same layer-2 input activation was evaluated by the current native CPU path and CUDA expert kernel. The reference uses pinned GGML to_float weight decoding followed by an independent FP64 accumulation; it is independent of both production dot paths but does not independently validate codec decoding. This isolates one expert output calculation, not a router-weighted layer result or service-level causal proof.",
    "summary": {
        "cpu_cuda_all_values_differ": all(r["cpu_cuda_differing_f32_words"] == r["cpu_cuda_total_f32_words"] for r in records),
        "cpu_relative_l1_range": [min(r["cpu_relative_l1_vs_fp64_reference"] for r in records), max(r["cpu_relative_l1_vs_fp64_reference"] for r in records)],
        "cuda_relative_l1_range": [min(r["cuda_relative_l1_vs_fp64_reference"] for r in records), max(r["cuda_relative_l1_vs_fp64_reference"] for r in records)],
        "cpu_cuda_relative_l1_range": [min(r["cpu_cuda_relative_l1"] for r in records), max(r["cpu_cuda_relative_l1"] for r in records)],
        "minimum_host_gib": min(r["minimum_host_gib"] for r in records),
        "minimum_admission_gib": min(r["minimum_admission_gib"] for r in records),
        "all_cgroup_memory_events_zero": all(not any(r["cgroup_memory_events_max"].values()) for r in records),
    },
    "experts": records,
}
if not summary["activation_sha256_verified"] or not summary["all_cpu_owned_experts_tested"] or not summary["summary"]["cpu_cuda_all_values_differ"] or not summary["summary"]["all_cgroup_memory_events_zero"]:
    raise SystemExit("summary invariant failed")
(HERE / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
