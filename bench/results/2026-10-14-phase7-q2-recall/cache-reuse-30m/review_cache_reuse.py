#!/usr/bin/env python3
"""Independent quality and cache-hit review for the Q2 sustained run."""
import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    codes = result["expected_codes"]
    rows = [json.loads(line) for line in args.requests.read_text().splitlines() if line]
    checks = []
    for row in rows:
        answer = row.get("content", "")
        positions = [answer.find(code) for code in codes]
        cache_tokens = max(row.get("cached_prompt_tokens", 0),
                           row.get("timings", {}).get("cache_n", 0))
        checks.append({
            "request_index": row.get("request_index"),
            "prompt_tokens": row.get("prompt_tokens"),
            "completion_tokens": row.get("completion_tokens"),
            "cached_prompt_tokens": row.get("cached_prompt_tokens", 0),
            "engine_cache_tokens": row.get("timings", {}).get("cache_n", 0),
            "codes_once_in_order": all(answer.count(code) == 1 for code in codes)
                and all(position >= 0 for position in positions)
                and positions == sorted(positions),
            "cache_hit": cache_tokens > 0,
            "error": row.get("error"),
        })
    passed = (result.get("status") == "pass"
              and result.get("measured_duration_s", 0) >= result.get("requested_duration_s", 1)
              and len(checks) == result.get("request_count")
              and result.get("failed_or_wrong_requests") == 0
              and all(row["prompt_tokens"] == 7498 and row["completion_tokens"] > 0
                      and row["codes_once_in_order"] and row["cache_hit"] and not row["error"]
                      for row in checks))
    review = {
        "overall_pass": passed,
        "request_count": len(checks),
        "checked_codes": codes,
        "expected_prompt_tokens": 7498,
        "all_requests_reused_prompt": all(row["cache_hit"] for row in checks),
        "requests": checks,
    }
    args.output.write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps({k: v for k, v in review.items() if k != "requests"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
