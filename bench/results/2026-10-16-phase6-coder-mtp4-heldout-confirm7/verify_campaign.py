#!/usr/bin/env python3
"""Independently qualify exact answers, pair identity, and memory floor."""
import json
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign" / "campaign.json"
GIB = 1024 ** 3


def main() -> int:
    inputs = json.loads((ROOT / "inputs.json").read_text())
    workload = json.loads((ROOT / "workloads.json").read_text())["workloads"][0]
    expected = workload["expected_answer"]
    campaign = json.loads(CAMPAIGN.read_text())
    errors = []
    available, admission, samples, events = [], [], 0, []
    rows_by_pair = {}

    config = json.loads((ROOT / "config.json").read_text())
    binary = Path(config["exe"])
    if not binary.is_file() or hashlib.sha256(binary.read_bytes()).hexdigest() != inputs["binary_sha256"]:
        errors.append("service binary is missing or its SHA256 differs from inputs.json")

    if len(campaign.get("runs", [])) != 14:
        errors.append(f"expected 14 runs, got {len(campaign.get('runs', []))}")
    for run in campaign.get("runs", []):
        run_dir = Path(run["directory"])
        if run.get("status") != "pass" or run.get("request_status") != "pass":
            errors.append(f"block {run.get('block')} window {run.get('window')}: run/request failed")
        record = json.loads((run_dir / "requests.json").read_text())
        measured = [row for row in record["checks"] if not row.get("warmup")]
        if len(measured) != 1:
            errors.append(f"{run_dir}: expected one measured request, found {len(measured)}")
            continue
        request = measured[0]
        response = request["response"]["choices"][0]["message"].get("content", "")
        usage = request["response"].get("usage", {})
        engine = request.get("metrics_after", {}).get("engine", {})
        if response != expected:
            errors.append(f"{run_dir}: answer mismatch: {response!r}")
        if usage.get("prompt_tokens") != 512:
            errors.append(f"{run_dir}: prompt token count is {usage.get('prompt_tokens')}")
        if run.get("engine", {}).get("expert_slots") != engine.get("expert_slots"):
            errors.append(f"{run_dir}: campaign and request expert-slot counts differ")
        rows_by_pair.setdefault(run["block"], {})[run["window"]] = engine

        supervisor = json.loads((run_dir / "supervisor" / "result.json").read_text())
        available.append(supervisor.get("minimum_available_bytes", 0))
        admission.append(supervisor.get("minimum_admission_available_bytes", 0))
        memory_path = run_dir / "supervisor" / "memory.jsonl"
        with memory_path.open() as stream:
            for line in stream:
                sample = json.loads(line)
                samples += 1
                for cg in sample.get("cgroups", []):
                    events.extend(cg.get("memory_events", {}).values())

    for block, arms in rows_by_pair.items():
        if set(arms) != {0, 4}:
            errors.append(f"block {block}: missing an MTP arm")
        elif (arms[0].get("expert_slots") != arms[4].get("expert_slots") or
              arms[0].get("kv") != arms[4].get("kv")):
            errors.append(f"block {block}: actual expert residency or KV differs")
    if not available or min(available) < 6 * GIB:
        errors.append("host-availability floor failed or missing")
    if not admission or min(admission) < 6 * GIB:
        errors.append("admission-availability floor failed or missing")
    if not events or max(events) != 0:
        errors.append("cgroup memory events were nonzero or missing")
    comparison = campaign.get("comparisons", [{}])[0]
    if not comparison.get("qualified_for_timing_interpretation"):
        errors.append("paired timing comparison is not qualified")

    summary = {
        "runs": len(campaign.get("runs", [])),
        "exact_answer": expected,
        "all_answers_match": not any("answer mismatch" in error for error in errors),
        "paired_timing_qualified": comparison.get("qualified_for_timing_interpretation"),
        "median_decode_tps_delta_percent": comparison.get("median_decode_tps_delta_percent"),
        "decode_tps_bootstrap_95pct_percent": comparison.get("bootstrap_95pct_median_interval_percent"),
        "minimum_host_available_gib": min(available) / GIB if available else None,
        "minimum_admission_available_gib": min(admission) / GIB if admission else None,
        "memory_samples": samples,
        "maximum_cgroup_memory_event": max(events) if events else None,
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))
    (ROOT / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
