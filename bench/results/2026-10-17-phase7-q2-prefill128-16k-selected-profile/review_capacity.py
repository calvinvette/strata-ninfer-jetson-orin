#!/usr/bin/env python3
"""Independent checks for selected-profile long-context capacity runs."""
import argparse
import json
from pathlib import Path

GIB = 1024 ** 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--supervisor", type=Path, required=True)
    parser.add_argument("--memory", type=Path, required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = json.loads(args.result.read_text())
    workload = json.loads(args.workload.read_text())["workloads"][0]
    supervisor = json.loads(args.supervisor.read_text())
    answer = result.get("answer", "")
    codes = workload["expected_codes"]
    positions = [answer.find(code) for code in codes]
    marker_pass = (all(answer.count(code) == 1 for code in codes) and
                   all(pos >= 0 for pos in positions) and positions == sorted(positions))
    recovery = result.get("recovery", {}).get("response", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
    response = result.get("recall", {}).get("response", {})
    usage = response.get("usage", {})
    timings = response.get("timings", {})
    engine = result.get("capabilities", {}).get("engine", {})
    samples = [json.loads(line) for line in args.memory.read_text().splitlines() if line.strip()]
    scoped = [cg for sample in samples for cg in sample.get("cgroups", [])
              if cg.get("max_bytes") == 28 * GIB and "run-" in cg.get("path", "")]
    events = {name: max((cg.get("memory_events", {}).get(name, 0) for cg in scoped), default=-1)
              for name in ("low", "high", "max", "oom", "oom_kill")}
    floor = 6 * GIB
    checks = {
        "runner_pass": result.get("status") == "pass",
        "supervisor_pass": supervisor.get("status") == "pass" and supervisor.get("returncode") == 0,
        "configured_context": result.get("configured_context"),
        "expected_context": args.context,
        "kv_format": engine.get("kv"),
        "actual_expert_slots": engine.get("expert_slots"),
        "actual_expert_cache_mib": engine.get("expert_cache_mib"),
        "mtp_max": engine.get("mtp_max"),
        "pool_workers": engine.get("pool_workers"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "expected_prompt_tokens": workload["prompt_tokens"],
        "engine_prompt_tokens": timings.get("prompt_n"),
        "cached_prompt_tokens": timings.get("cache_n"),
        "completion_tokens": usage.get("completion_tokens"),
        "three_markers_once_in_order": marker_pass,
        "marker_positions": positions,
        "same_service_recovery": "RECOVERED" in recovery,
        "minimum_host_gib": supervisor.get("minimum_available_bytes", 0) / GIB,
        "minimum_admission_gib": supervisor.get("minimum_admission_available_bytes", 0) / GIB,
        "required_floor_gib": floor / GIB,
        "observed_28g_scope_samples": len(scoped),
        "maximum_cgroup_memory_events": events,
        "prompt_seconds": timings.get("prompt_ms", 0) / 1000,
        "client_elapsed_seconds": result.get("recall", {}).get("elapsed_s"),
    }
    passed = (checks["runner_pass"] and checks["supervisor_pass"] and
              checks["configured_context"] == args.context and
              checks["kv_format"] == "fp16" and checks["actual_expert_slots"] == 3000 and
              checks["actual_expert_cache_mib"] == 3955 and
              checks["mtp_max"] == 0 and checks["pool_workers"] == 8 and
              checks["prompt_tokens"] == workload["prompt_tokens"] and
              checks["engine_prompt_tokens"] == workload["prompt_tokens"] and
              checks["cached_prompt_tokens"] == 0 and
              isinstance(checks["completion_tokens"], int) and checks["completion_tokens"] > 0 and
              marker_pass and checks["same_service_recovery"] and
              checks["minimum_host_gib"] >= 6 and checks["minimum_admission_gib"] >= 6 and
              bool(scoped) and all(value == 0 for value in events.values()))
    review = {"status": "pass" if passed else "fail", "independent_review": True,
              "scope": "one selected Q2_0 MTP-off capacity and retrieval/recovery cell",
              "checks": checks, "expected_codes": codes, "answer": answer,
              "recovery_answer": recovery}
    args.output.write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps(review, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
