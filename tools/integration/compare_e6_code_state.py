#!/usr/bin/env python3
"""Compare accepted-prefix tokens/state and code quality for E6 code captures."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "integration")]
from evaluate_e6_code_task import evaluate  # noqa: E402
from pool_worker_screen import read_accepted_prefix_trace  # noqa: E402


def compare_traces(strata: list[dict], ninfer: list[dict]) -> dict:
    same_length = len(strata) == len(ninfer)
    tokens_equal = same_length and all(a["token_ids"] == b["token_ids"]
                                       for a, b in zip(strata, ninfer))
    state_equal = same_length and all(a["state"] == b["state"]
                                      for a, b in zip(strata, ninfer))
    first_difference = None
    if not same_length:
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
        "token_ids_equal": bool(tokens_equal),
        "persistent_state_equal": bool(state_equal),
        "canonical_strata_trace_sha256": hashlib.sha256(canonical).hexdigest(),
        "first_difference": first_difference,
    }


def check_quality(path: Path) -> dict:
    requests = json.loads(path.read_text())
    outcomes = []
    for row in requests.get("checks", []):
        text = row.get("response", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            outcome = evaluate(text)
            outcome.update(warmup=bool(row.get("warmup")), api_status=row.get("status"))
        except Exception as exc:
            outcome = {"warmup": bool(row.get("warmup")), "api_status": row.get("status"),
                       "passed": False, "error": f"{type(exc).__name__}: {exc}"}
        if row.get("status") != "pass":
            outcome["passed"] = False
        outcomes.append(outcome)
    return {"outcomes": outcomes,
            "all_passed": len(outcomes) == 2 and all(row.get("passed") for row in outcomes),
            "answer_hashes": [row.get("code_sha256") for row in outcomes]}


def resource_summary(directory: Path) -> dict:
    result = json.loads((directory / "result.json").read_text())
    samples = [json.loads(line) for line in (directory / "memory.jsonl").read_text().splitlines()]
    if not samples:
        raise ValueError(f"no memory telemetry in {directory}")
    def oom_values(sample):
        return [node.get("memory_events", {}).get("oom_kill", 0)
                for node in sample.get("cgroups", [])]
    initial = oom_values(samples[0])
    final = oom_values(samples[-1])
    return {
        "supervisor_status": result.get("status"),
        "minimum_available_gib": min(row["available_bytes"] for row in samples) / 1024**3,
        "minimum_admission_available_gib": min(row["admission_available_bytes"] for row in samples) / 1024**3,
        "maximum_swap_used_gib": max(row.get("swap_used_bytes", 0) for row in samples) / 1024**3,
        "oom_kill_counter_initial": max(initial, default=0),
        "oom_kill_counter_final": max(final, default=0),
        "oom_kill_counter_delta": max(final, default=0) - max(initial, default=0),
        "memory_samples": len(samples),
    }


def compare_capture(strata_log: Path, ninfer_log: Path,
                    strata_requests: Path, ninfer_requests: Path,
                    strata_dir: Path | None = None, ninfer_dir: Path | None = None) -> dict:
    strata_quality, ninfer_quality = check_quality(strata_requests), check_quality(ninfer_requests)
    trace = compare_traces(read_accepted_prefix_trace(strata_log),
                           read_accepted_prefix_trace(ninfer_log))
    result = {
        "strata_quality_passed": strata_quality["all_passed"],
        "ninfer_quality_passed": ninfer_quality["all_passed"],
        "strata_code_sha256": strata_quality["answer_hashes"],
        "ninfer_code_sha256": ninfer_quality["answer_hashes"],
        "answers_equal": strata_quality["answer_hashes"] == ninfer_quality["answer_hashes"],
        **trace,
    }
    if strata_dir is not None:
        result["strata_resources"] = resource_summary(strata_dir)
    if ninfer_dir is not None:
        result["ninfer_resources"] = resource_summary(ninfer_dir)
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
    parser.add_argument("--strata-dir", type=Path)
    parser.add_argument("--ninfer-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare_capture(args.strata_log, args.ninfer_log,
                             args.strata_requests, args.ninfer_requests,
                             args.strata_dir, args.ninfer_dir)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
