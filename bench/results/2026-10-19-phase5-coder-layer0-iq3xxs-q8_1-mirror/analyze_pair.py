#!/usr/bin/env python3
"""Summarize the matched fixed/adaptive Coder Q8_1 diagnostic service arms."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARMS = ROOT / "service-pair"


def load_arm(name):
    path = ARMS / name
    analysis = json.loads((path / "run/analysis.json").read_text())
    supervisor = json.loads((path / "supervisor/result.json").read_text())
    if supervisor["status"] != "pass" or supervisor["returncode"] != 0:
        raise RuntimeError(f"{name}: supervised run failed")
    if len(analysis["requests"]) != 4 or any(len(item["ids"]) != 16 for item in analysis["requests"]):
        raise RuntimeError(f"{name}: expected four 16-token responses")
    event_max = {key: 0 for key in ("low", "high", "max", "oom", "oom_kill")}
    for sample_line in (path / "supervisor/memory.jsonl").read_text().splitlines():
        sample = json.loads(sample_line)
        for group in sample.get("cgroups", []):
            if group.get("max_bytes") is None:
                continue
            for key, value in group.get("memory_events", {}).items():
                if key in event_max:
                    event_max[key] = max(event_max[key], value)
    return {
        "binary_sha256": analysis["binary_sha256"],
        "opt_in": analysis["cpu_q8_1_dot"],
        "elapsed_s": supervisor["elapsed_s"],
        "minimum_host_available_gib": supervisor["minimum_available_bytes"] / 2**30,
        "minimum_admission_available_gib": supervisor["minimum_admission_available_bytes"] / 2**30,
        "maximum_cgroup_events": event_max,
        "adaptive_byte_verification_passes": analysis["adaptive_byte_verification_passes"],
        "adaptive_residency_verification_passes": analysis["adaptive_residency_verification_passes"],
        "requests": analysis["requests"],
        "analysis": analysis,
    }


identity = json.loads((ROOT / "artifact-identity.json").read_text())
report = {
    "experiment": "single same-day diagnostic control/mirror comparison; not a qualification",
    "source_commit": "9d3f86aa",
    "source_overlay_sha256": identity["source_overlay_sha256"],
    "model": {
        "repo": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
        "revision": "5348543e0147355ac9cbcb031184a3546350988e",
        "quantization": "IQ1_M, two shards",
    },
    "profile": "prompt-cache=0, spec=2, 8K context, 28-GiB MemoryMax, dynamic clocks",
    "paired_arms": {},
}

for policy, names in {
    "adaptive": ("control-v2", "mirror"),
    "fixed": ("fixed-control", "fixed-mirror"),
}.items():
    control, mirror = (load_arm(name) for name in names)
    if control["binary_sha256"] != mirror["binary_sha256"]:
        raise RuntimeError(f"{policy}: binary mismatch across paired arms")
    if control["opt_in"] or not mirror["opt_in"]:
        raise RuntimeError(f"{policy}: arms do not represent default and Q8_1 mirror")
    comparisons = []
    for left, right in zip(control["requests"], mirror["requests"]):
        if left["name"] != right["name"] or len(left["ids"]) != len(right["ids"]):
            raise RuntimeError(f"{policy}: request mismatch")
        keys = sorted(set(left["state"]) & set(right["state"]))
        comparisons.append({
            "name": left["name"],
            "token_differences": sum(a != b for a, b in zip(left["ids"], right["ids"])),
            "state_equal_fields": [key for key in keys if left["state"][key] == right["state"][key]],
            "state_different_fields": [key for key in keys if left["state"][key] != right["state"][key]],
        })
    report["paired_arms"][policy] = {
        "control": control,
        "q8_1_mirror": mirror,
        "comparison": comparisons,
    }
    for row in comparisons:
        print(policy, row["name"], "token differences", row["token_differences"],
              "state differences", len(row["state_different_fields"]))

target = ARMS / "analysis.json"
target.write_text(json.dumps(report, indent=2) + "\n")
print(f"wrote {target}")
