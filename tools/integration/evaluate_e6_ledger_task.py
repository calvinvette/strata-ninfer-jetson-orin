#!/usr/bin/env python3
"""Apply an exact-output oracle to E6 structured ledger API captures."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


EXPECTED = {
    "regions": {
        "EAST": {"count": 5, "sum": 36, "max_id": "R01", "max_amount": 14},
        "NORTH": {"count": 3, "sum": 21, "max_id": "R04", "max_amount": 12},
        "WEST": {"count": 4, "sum": 23, "max_id": "R08", "max_amount": 11},
    },
    "total": {"count": 12, "sum": 80},
}


def parse_answer(text: str) -> dict:
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    value = json.loads(text)
    if not isinstance(value, dict) or value != EXPECTED:
        raise AssertionError(f"expected exact ledger result {EXPECTED!r}; got {value!r}")
    return value


def evaluate_result(result: dict) -> dict:
    outcomes = []
    for row in result.get("checks", []):
        response = row.get("response") or {}
        text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            if row.get("status") != "pass" or not text:
                raise ValueError("request did not pass API workload checks")
            parse_answer(text)
            outcomes.append({"cell": row.get("cell"), "warmup": row.get("warmup"),
                             "passed": True,
                             "answer_sha256": hashlib.sha256(text.encode()).hexdigest()})
        except Exception as exc:  # preserve every failed response as a quality failure
            outcomes.append({"cell": row.get("cell"), "warmup": row.get("warmup"),
                             "passed": False, "error": f"{type(exc).__name__}: {exc}",
                             "answer_sha256": hashlib.sha256(text.encode()).hexdigest()})
    return {"outcomes": outcomes,
            "all_passed": bool(outcomes) and all(row["passed"] for row in outcomes)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("response_json", type=Path,
                        help="benchmark_control.py result JSON containing checks")
    args = parser.parse_args()
    result = json.loads(args.response_json.read_text())
    payload = {"source": str(args.response_json), **evaluate_result(result)}
    print(json.dumps(payload, indent=2))
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
