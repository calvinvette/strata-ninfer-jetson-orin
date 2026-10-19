#!/usr/bin/env python3
"""Summarize matched control and opt-in Q8_1 adaptive-state service runs."""
import argparse
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def accepted_prefix_states(path, state_keys):
    states = []
    marker = " state={STATE_HASH "
    for line in (path / "run/service.log").read_text(encoding="utf-8", errors="replace").splitlines():
        if "ACCEPTED_PREFIX " not in line or marker not in line:
            continue
        body = line.split(marker, 1)[1].split("}", 1)[0]
        fields = dict(re.findall(r"(\w+)=([0-9a-f,-]+)", body))
        if not set(state_keys) <= fields.keys():
            raise RuntimeError(f"{path}: incomplete accepted-prefix fingerprint")
        states.append({key: fields[key] for key in state_keys})
    return states


def load_arm(name, path):
    analysis = json.loads((path / "run/analysis.json").read_text())
    supervisor = json.loads((path / "supervisor/result.json").read_text())
    if supervisor["status"] != "pass" or supervisor["returncode"] != 0:
        raise RuntimeError(f"{name}: supervisor did not pass")
    requests = analysis["requests"]
    if len(requests) != 4 or any(len(request["ids"]) != 16 for request in requests):
        raise RuntimeError(f"{name}: expected four 16-token responses")

    events = {key: 0 for key in ("low", "high", "max", "oom", "oom_kill")}
    peak_cgroup = 0
    min_host = None
    min_admission = None
    for line in (path / "supervisor/memory.jsonl").read_text().splitlines():
        sample = json.loads(line)
        min_host = sample["available_bytes"] if min_host is None else min(min_host, sample["available_bytes"])
        admission = sample.get("admission_available_bytes")
        if admission is not None:
            min_admission = admission if min_admission is None else min(min_admission, admission)
        for group in sample.get("cgroups", []):
            if group.get("max_bytes") is not None:
                peak_cgroup = max(peak_cgroup, group.get("current_bytes", 0))
            for key, value in group.get("memory_events", {}).items():
                if key in events:
                    events[key] = max(events[key], value)
    return {
        "binary_sha256": analysis["binary_sha256"],
        "selector": analysis.get("cpu_q8_1_pair"),
        "opt_in": analysis["cpu_q8_1_dot"] or analysis.get("cpu_q8_1_pair") is not None,
        "adaptive_byte_verification_passes": analysis["adaptive_byte_verification_passes"],
        "adaptive_residency_verification_passes": analysis["adaptive_residency_verification_passes"],
        "elapsed_s": supervisor["elapsed_s"],
        "minimum_host_available_gib": min_host / 2**30,
        "minimum_admission_available_gib": min_admission / 2**30,
        "peak_supervised_cgroup_gib": peak_cgroup / 2**30,
        "maximum_observed_cgroup_events": events,
        "requests": requests,
        "accepted_prefix_states": accepted_prefix_states(
            path, requests[0]["state"].keys()),
        "analysis": analysis,
    }


def analyze_pair(label, arms, target_root):
    result = {name: load_arm(name, path) for name, path in arms.items()}
    control = result["control"]
    mirror = result["mirror"]
    if control["binary_sha256"] != mirror["binary_sha256"]:
        raise RuntimeError("paired arms used different service binaries")
    if control["opt_in"] or not mirror["opt_in"] or control["selector"] is not None:
        raise RuntimeError("arms do not represent default then opt-in CPU Q8_1")
    expected_selector = "iq2_s/q2_0@layer=1"
    if mirror["selector"] != expected_selector:
        raise RuntimeError(f"mirror selector is {mirror['selector']!r}, expected {expected_selector!r}")
    pairs = []
    prefix_pairs = []
    if len(control["accepted_prefix_states"]) != 64 or len(mirror["accepted_prefix_states"]) != 64:
        raise RuntimeError("expected exactly 16 accepted-prefix states for each of four requests")
    for left, right in zip(control["requests"], mirror["requests"]):
        pairs.append({
            "name": left["name"],
            "token_differences": sum(a != b for a, b in zip(left["ids"], right["ids"])),
            "state_equal_fields": [key for key in left["state"] if left["state"][key] == right["state"][key]],
            "state_different_fields": [key for key in left["state"] if left["state"][key] != right["state"][key]],
        })
    for request_index, name in enumerate(request["name"] for request in control["requests"]):
        start = request_index * 16
        left_trace = control["accepted_prefix_states"][start:start + 16]
        right_trace = mirror["accepted_prefix_states"][start:start + 16]
        differences = [[key for key in left if left[key] != right[key]]
                       for left, right in zip(left_trace, right_trace)]
        first = next((index + 1 for index, fields in enumerate(differences) if fields), None)
        prefix_pairs.append({
            "name": name,
            "compared_commits": len(differences),
            "commits_with_state_differences": sum(bool(fields) for fields in differences),
            "first_different_commit": first,
            "first_difference_fields": differences[first - 1] if first is not None else [],
            "fields_differing_by_commit": differences,
        })
    conclusion = (
        "This is a single paired state diagnostic that changes only CPU-owned IQ2_S/Q2_0 experts on model layer 1. "
        "Token-ID and persistent-state differences show whether that layer-scoped route is sufficient to perturb "
        "the tested continuation. One prompt sequence cannot establish answer-quality impact or qualify adaptive "
        "migration, and it is not a performance comparison."
    )
    report = {
        "experiment": f"single paired {label}-state service sequence; diagnostic only",
        "source_commit": "c5f9f319",
        "model": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M, revision 5348543e0147355ac9cbcb031184a3546350988e",
        "profile": ("adapt-every=4, adapt-swaps=8, accepted-only" if label == "adaptive" else
                    "adaptive swaps disabled") + "; prompt-cache=0; spec=2; 8K max context",
        "paired_arms": result,
        "cross_arm_request_comparison": pairs,
        "accepted_prefix_comparison": prefix_pairs,
        "route_selector": mirror["selector"],
        "conclusion": conclusion,
    }
    target = target_root / f"service-test-{label}-pair-analysis.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    for item in pairs:
        print(f"{item['name']}: token differences={item['token_differences']}; "
              f"state fields differ={item['state_different_fields']}")
    print(f"wrote {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "service-test",
                        help="directory containing control-v2, mirror, fixed-control and fixed-mirror")
    args = parser.parse_args()
    pairs = {
        "adaptive": {"control": args.root / "control-v2", "mirror": args.root / "mirror"},
        "fixed": {"control": args.root / "fixed-control", "mirror": args.root / "fixed-mirror"},
    }
    output_root = ROOT if args.root.resolve() == (ROOT / "service-test").resolve() else args.root
    for label, arms in pairs.items():
        analyze_pair(label, arms, output_root)


if __name__ == "__main__":
    main()
