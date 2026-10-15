#!/usr/bin/env python3
"""Independently check each retained sustained Q2_0 retrieval response."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--expected-prompt-tokens", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    codes = result["expected_codes"]
    rows = [json.loads(line) for line in args.requests.read_text().splitlines() if line]
    checks = []
    for row in rows:
        content = row.get("content", "")
        positions = [content.find(code) for code in codes]
        checks.append({
            "request_index": row.get("request_index"),
            "prompt_tokens": row.get("prompt_tokens"),
            "completion_tokens": row.get("completion_tokens"),
            "markers_once_in_order": all(content.count(code) == 1 for code in codes)
                and all(position >= 0 for position in positions)
                and positions == sorted(positions),
            "uncached": row.get("cached_prompt_tokens") == 0
                and row.get("timings", {}).get("cache_n", 0) == 0,
            "error": row.get("error"),
        })
    passed = (result.get("status") == "pass"
              and result.get("precondition", {}).get("prompt_tokens") == args.expected_prompt_tokens
              and len(checks) == result.get("request_count")
              and result.get("failed_or_wrong_requests") == 0
              and all(row["prompt_tokens"] == args.expected_prompt_tokens
                      and row["completion_tokens"] > 0 and row["markers_once_in_order"]
                      and row["uncached"] and not row["error"] for row in checks))
    review = {"overall_pass": passed, "request_count": len(checks),
              "expected_prompt_tokens": args.expected_prompt_tokens,
              "checked_codes": codes,
              "all_full_prompts_uncached": all(row["uncached"] for row in checks),
              "requests": checks}
    args.output.write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps({key: value for key, value in review.items() if key != "requests"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
