#!/usr/bin/env python3
"""Independently check the retained serial and two-slot API outcomes."""
import argparse
import json
from pathlib import Path


def check_rows(rows, expected):
    checks = []
    for row, prompt_tokens, codes in zip(rows, (7498, 15003), expected):
        content = row.get("content", "")
        positions = [content.find(code) for code in codes]
        checks.append({
            "cell": row.get("cell"),
            "prompt_tokens": row.get("prompt_tokens"),
            "completion_tokens": row.get("completion_tokens"),
            "markers_once_in_order": all(content.count(code) == 1 for code in codes)
                and all(position >= 0 for position in positions)
                and positions == sorted(positions),
            "uncached": row.get("cached_prompt_tokens") == 0
                and row.get("timings", {}).get("cache_n", 0) == 0,
            "pass": row.get("quality_pass") is True
                and row.get("prompt_tokens") == prompt_tokens
                and row.get("completion_tokens", 0) == 41
                and row.get("cached_prompt_tokens") == 0
                and row.get("timings", {}).get("cache_n", 0) == 0
                and all(content.count(code) == 1 for code in codes)
                and all(position >= 0 for position in positions)
                and positions == sorted(positions),
        })
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run = json.loads(args.result.read_text())
    parallel = run["parallel2"]
    expected = [row["expected_codes"] for row in parallel["requests"]]
    serial_checks = check_rows(run["serial"]["requests"], expected)
    parallel_checks = check_rows(parallel["requests"], expected)
    passed = (run.get("status") == "pass"
              and len(run["serial"]["requests"]) == 2
              and len(parallel["requests"]) == 2
              and len(serial_checks) == 2
              and len(parallel_checks) == 2 and all(x["pass"] for x in serial_checks)
              and all(x["pass"] for x in parallel_checks)
              and parallel.get("batch_slots_reported") == 2
              and run.get("max_running_observed", 0) >= 2
              and run.get("max_active_slots_observed", 0) >= 2)
    review = {"overall_pass": passed,
              "serial": serial_checks,
              "parallel2": parallel_checks,
              "batch_slots_reported": parallel.get("batch_slots_reported"),
              "max_running_observed": run.get("max_running_observed"),
              "max_active_slots_observed": run.get("max_active_slots_observed")}
    args.output.write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps(review, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
