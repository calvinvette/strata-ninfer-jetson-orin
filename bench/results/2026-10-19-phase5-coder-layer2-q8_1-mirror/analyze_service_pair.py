#!/usr/bin/env python3
"""Summarize matched control and opt-in Q8_1 adaptive-state service runs."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


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
        "opt_in": analysis["cpu_q8_1_dot"],
        "adaptive_byte_verification_passes": analysis["adaptive_byte_verification_passes"],
        "adaptive_residency_verification_passes": analysis["adaptive_residency_verification_passes"],
        "elapsed_s": supervisor["elapsed_s"],
        "minimum_host_available_gib": min_host / 2**30,
        "minimum_admission_available_gib": min_admission / 2**30,
        "peak_supervised_cgroup_gib": peak_cgroup / 2**30,
        "maximum_observed_cgroup_events": events,
        "requests": requests,
        "analysis": analysis,
    }


def analyze_pair(label, arms, target_root):
    result = {name: load_arm(name, path) for name, path in arms.items()}
    control = result["control"]
    mirror = result["mirror"]
    if control["binary_sha256"] != mirror["binary_sha256"]:
        raise RuntimeError("paired arms used different service binaries")
    if control["opt_in"] or not mirror["opt_in"]:
        raise RuntimeError("arms do not represent default then opt-in CPU Q8_1")
    pairs = []
    for left, right in zip(control["requests"], mirror["requests"]):
        pairs.append({
            "name": left["name"],
            "token_differences": sum(a != b for a, b in zip(left["ids"], right["ids"])),
            "state_equal_fields": [key for key in left["state"] if left["state"][key] == right["state"][key]],
            "state_different_fields": [key for key in left["state"] if left["state"][key] != right["state"][key]],
        })
    conclusion = (
        "The first three request token IDs matched across arms; the continuation differed at 10/16 tokens. "
        "Persistent-state hashes differed in multiple fields. Exact IQ4_NL down-projection parity therefore "
        "does not establish whole-expert or service-state parity, and this one pair does not qualify a fix."
        if label == "adaptive" else
        "The long request differed at 3/16 token IDs, while the first short request, recovery and continuation "
        "matched. Persistent-state hashes differed in multiple fields. Exact IQ4_NL down-projection parity "
        "therefore does not establish whole-expert or service-state parity, and this one pair does not qualify a fix."
    )
    report = {
        "experiment": f"single paired {label}-state service sequence; diagnostic only",
        "source_commit": "0ddbf031",
        "model": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "profile": ("adapt-every=4, adapt-swaps=8, accepted-only" if label == "adaptive" else
                    "adaptive swaps disabled") + "; prompt-cache=0; spec=2; 8K max context",
        "paired_arms": result,
        "cross_arm_request_comparison": pairs,
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
