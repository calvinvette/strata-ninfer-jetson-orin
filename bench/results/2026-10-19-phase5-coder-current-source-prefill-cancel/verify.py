#!/usr/bin/env python3
"""Independent review of a current-source Coder prefill-cancel recovery run."""
import argparse
import json
from pathlib import Path

KEYS = ("L", "gdn", "ple", "tail", "dead", "pooled", "pooled_full", "kv", "mtp", "stale", "ple_prev")


def require(ok, message):
    if not ok:
        raise SystemExit(message)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--result", type=Path, default=Path(__file__).parent / "result.json")
parser.add_argument("--supervisor", type=Path, default=Path(__file__).parent / "supervisor-retry")
args = parser.parse_args()
result = json.loads(args.result.read_text())
cancel, recovery = result["checks"]
require(cancel["check"] == "cancel_long_prefill" and cancel["status"] == "pass", "prefill cancel failed")
observed = cancel["engine_cancellation"]
require(observed["prompt_tokens"] == 7501 and observed["read_tokens"] == 512,
        "engine did not record the expected in-progress prompt position")
require(observed["generated_tokens"] == 0, "engine generated output after cancellation")
require(recovery["check"] == "short_request_recovery" and recovery["status"] == "pass",
        "same-service recovery failed")
require(recovery["response"]["choices"][0]["message"]["content"].strip() == "Hello Orin!",
        "unexpected recovered response")
comparison = result["recovery_state_comparison"]
require(comparison["all_fields_equal"] is True, "recovery and fresh-service states differ")
require(comparison["reference_answer"] == "Hello Orin!", "fresh-service response differs")
require(all(comparison["recovered_state"].get(k) == comparison["reference_state"].get(k) for k in KEYS),
        "one or more persistent state fingerprints differ")

summary = json.loads((args.supervisor / "result.json").read_text())
rows = [json.loads(line) for line in (args.supervisor / "memory.jsonl").read_text().splitlines()]
scopes = [cg for row in rows for cg in row["cgroups"] if cg["path"].endswith(".scope")]
events = {key: max(cg["memory_events"].get(key, 0) for cg in scopes)
          for key in ("low", "high", "max", "oom", "oom_kill")}
require(summary["status"] == "pass" and len(rows) == 71, "supervised run failed or sample count changed")
require(not any(events.values()), f"cgroup memory events observed: {events}")
require(summary["minimum_available_bytes"] >= 6 * 1024**3, "six-GiB host floor breached")
require(summary["minimum_admission_available_bytes"] >= 6 * 1024**3,
        "six-GiB admission floor breached")

review = {"passed": True, "prompt_tokens": observed["prompt_tokens"],
          "read_tokens_at_cancel": observed["read_tokens"], "generated_after_cancel": observed["generated_tokens"],
          "recovery_answer": "Hello Orin!", "fresh_state_equal": True,
          "state_fields": list(KEYS), "supervisor_samples": len(rows),
          "minimum_available_bytes": summary["minimum_available_bytes"],
          "minimum_admission_available_bytes": summary["minimum_admission_available_bytes"],
          "cgroup_event_maxima": events}
output = Path(__file__).parent / "verification.json"
output.write_text(json.dumps(review, indent=2) + "\n")
print(json.dumps(review, indent=2))
