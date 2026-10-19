#!/usr/bin/env python3
"""Independent output and memory review for run_sequence.py."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--supervisor", type=Path, required=True)
    ap.add_argument("--samples", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    run = json.loads(args.result.read_text())
    supervisor = json.loads(args.supervisor.read_text())
    samples = [json.loads(line) for line in args.samples.read_text().splitlines() if line]
    short = "EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768"
    long_codes = ["MAPLE-ORBIT-731", "COBALT-HARBOR-284", "VELVET-COPPER-956"]
    before = run.get("short_before", {})
    after = run.get("short_after", {})
    long = run.get("long", {})
    long_text = long.get("content", "")
    positions = [long_text.find(code) for code in long_codes]
    event_values = [event for row in samples for cg in row.get("cgroups", [])
                    for event in cg.get("memory_events", {}).values()]
    checks = {
        "runner_passed": run.get("status") == "pass",
        "same_candidate_binary": run.get("engine_sha256") ==
            "320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932",
        "short_before_exact_oracle": before.get("content", "").strip() == short,
        "short_after_exact_oracle": after.get("content", "").strip() == short,
        "short_prompts_512_uncached": all(row.get("prompt_tokens") == 512 and
            row.get("cached_prompt_tokens") == 0 and row.get("timings", {}).get("cache_n", 0) == 0
            for row in (before, after)),
        "long_prompt_7498_uncached": long.get("prompt_tokens") == 7498 and
            long.get("cached_prompt_tokens") == 0 and long.get("timings", {}).get("cache_n", 0) == 0,
        "long_codes_once_in_order": all(long_text.count(code) == 1 for code in long_codes) and
            all(pos >= 0 for pos in positions) and positions == sorted(positions),
        "supervisor_passed": supervisor.get("status") == "pass" and supervisor.get("returncode") == 0,
        "minimum_host_above_6gib": supervisor.get("minimum_available_bytes", 0) >= 6 * 2**30,
        "all_sampled_cgroup_events_zero": bool(samples) and all(value == 0 for value in event_values),
    }
    review = {"overall_pass": all(checks.values()), "checks": checks,
              "memory_samples": len(samples),
              "minimum_host_gib": supervisor.get("minimum_available_bytes", 0) / 2**30,
              "minimum_admission_gib": supervisor.get("minimum_admission_available_bytes", 0) / 2**30,
              "minimum_sampled_host_gib": min(row["available_bytes"] for row in samples) / 2**30,
              "minimum_sampled_admission_gib": min(row["admission_available_bytes"] for row in samples) / 2**30,
              "short_answer": short, "long_codes": long_codes}
    args.output.write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps(review, indent=2))
    return 0 if review["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
