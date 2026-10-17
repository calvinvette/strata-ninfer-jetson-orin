#!/usr/bin/env python3
"""Check the Q2_0 long-context answer against an independent arithmetic oracle."""
import json
from pathlib import Path
import re
import sys


def main() -> int:
    source = Path(sys.argv[1])
    result = json.loads(source.read_text())
    answer = result["answer"]
    codes = result["quality"]["expected_codes"]
    suffixes = [int(re.search(r"-(\d+)$", code).group(1)) for code in codes]
    expected_sum = sum(suffixes)
    match = re.search(r"(?:^|,\s*)SUM=(\d+)(?:$|\s)", answer)
    review = {
        "codes": codes,
        "codes_once_in_order": all(answer.count(code) == 1 for code in codes)
            and [answer.find(code) for code in codes] == sorted(answer.find(code) for code in codes),
        "suffixes": suffixes,
        "expected_sum": expected_sum,
        "observed_sum": int(match.group(1)) if match else None,
        "sum_pass": bool(match and int(match.group(1)) == expected_sum),
        "recovery": result["recovery"]["response"]["choices"][0]["message"]["content"],
    }
    review["overall_pass"] = (review["codes_once_in_order"] and review["sum_pass"]
                              and review["recovery"] == "RECOVERED")
    destination = source.with_name("quality-review.json")
    destination.write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps(review, indent=2))
    return 0 if review["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
