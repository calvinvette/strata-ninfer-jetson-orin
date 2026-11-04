#!/usr/bin/env python3
"""Compare accepted-prefix state for a paired E6 ledger task capture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "integration")]
from evaluate_e6_ledger_task import evaluate_result  # noqa: E402
from pool_worker_screen import read_accepted_prefix_trace  # noqa: E402


def compare_traces(strata: list[dict], ninfer: list[dict]) -> dict:
    token_equal = len(strata) == len(ninfer) and all(
        left["token_ids"] == right["token_ids"] for left, right in zip(strata, ninfer))
    state_equal = len(strata) == len(ninfer) and all(
        left["state"] == right["state"] for left, right in zip(strata, ninfer))
    first_difference = None
    if len(strata) != len(ninfer):
        first_difference = {"index": min(len(strata), len(ninfer)),
                            "reason": "trace lengths differ",
                            "strata_length": len(strata), "ninfer_length": len(ninfer)}
    else:
        for index, (left, right) in enumerate(zip(strata, ninfer)):
            if left != right:
                first_difference = {"index": index,
                                    "token_ids_equal": left["token_ids"] == right["token_ids"],
                                    "state_equal": left["state"] == right["state"]}
                break
    canonical = json.dumps(strata, sort_keys=True, separators=(",", ":")).encode()
    return {
        "trace_entries": len(strata),
        "strata_committed_tokens": sum(len(row["token_ids"]) for row in strata),
        "ninfer_committed_tokens": sum(len(row["token_ids"]) for row in ninfer),
        "token_ids_equal": token_equal,
        "persistent_state_equal": state_equal,
        "canonical_strata_trace_sha256": hashlib.sha256(canonical).hexdigest(),
        "first_difference": first_difference,
    }


def compare_capture(strata_log: Path, ninfer_log: Path,
                    strata_requests: Path, ninfer_requests: Path) -> dict:
    strata_trace = read_accepted_prefix_trace(strata_log)
    ninfer_trace = read_accepted_prefix_trace(ninfer_log)
    strata_quality = evaluate_result(json.loads(strata_requests.read_text()))
    ninfer_quality = evaluate_result(json.loads(ninfer_requests.read_text()))
    trace_result = compare_traces(strata_trace, ninfer_trace)
    strata_answers = [row.get("answer_sha256") for row in strata_quality["outcomes"]]
    ninfer_answers = [row.get("answer_sha256") for row in ninfer_quality["outcomes"]]
    result = {
        "strata_quality_passed": strata_quality["all_passed"],
        "ninfer_quality_passed": ninfer_quality["all_passed"],
        "strata_answer_hashes": strata_answers,
        "ninfer_answer_hashes": ninfer_answers,
        "answers_equal": strata_answers == ninfer_answers,
        **trace_result,
    }
    result["passed"] = bool(
        result["strata_quality_passed"] and result["ninfer_quality_passed"] and
        result["answers_equal"] and result["token_ids_equal"] and
        result["persistent_state_equal"] and result["trace_entries"] > 0)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strata-log", type=Path, required=True)
    parser.add_argument("--ninfer-log", type=Path, required=True)
    parser.add_argument("--strata-requests", type=Path, required=True)
    parser.add_argument("--ninfer-requests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare_capture(args.strata_log, args.ninfer_log,
                             args.strata_requests, args.ninfer_requests)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
