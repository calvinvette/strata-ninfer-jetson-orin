#!/usr/bin/env python3
"""Independently review int8 MTP token/state parity and supervisor limits."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run-2048"
SUPERVISOR = ROOT / "supervisor-2048"
STATE_KEYS = ("L", "gdn", "ple", "tail", "dead", "pooled", "pooled_full", "kv", "ple_prev")


def require(test, message):
    if not test:
        raise SystemExit(message)


data = json.loads((RUN / "results.json").read_text())
require(data["kv_format"] == "int8", "result is not the int8 KV cell")
require([arm["spec"] for arm in data["arms"]] == [0, 2, 3, 4], "unexpected MTP arms")
reference = data["arms"][0]["records"][0]
require(len(reference["ids"]) == 16, "reference did not publish 16 tokens")
review = {"passed": True, "kv_format": "int8", "checks": []}
for arm in data["arms"]:
    record = arm["records"][0]
    require(record["finish"] == "length", f"{arm['name']}: unexpected finish reason")
    require(len(record["ids"]) == 16, f"{arm['name']}: unexpected token count")
    require(set(STATE_KEYS) <= record["state"].keys(), f"{arm['name']}: incomplete state")
    require(record["accepted_prefix_trace"], f"{arm['name']}: missing prefix trace")
    require([t for row in record["accepted_prefix_trace"] for t in row["token_ids"]] == record["ids"],
            f"{arm['name']}: prefix trace does not publish the response")
    require(arm["engine_sha256"] == "b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa",
            f"{arm['name']}: binary identity mismatch")

    prefix_states = {}
    count = 0
    for row in reference["accepted_prefix_trace"]:
        count += row["committed"]
        prefix_states[count] = row["state"]
    candidate_prefixes = {}
    count = 0
    for row in record["accepted_prefix_trace"]:
        count += row["committed"]
        candidate_prefixes[count] = row["state"]
    shared = sorted(prefix_states.keys() & candidate_prefixes.keys())
    require(shared, f"{arm['name']}: no shared commit boundaries")
    differing = [key for key in STATE_KEYS if reference["state"].get(key) != record["state"].get(key)]
    require(not differing, f"{arm['name']}: final state differs: {differing}")
    require(reference["ids"] == record["ids"], f"{arm['name']}: output IDs differ")
    boundary_differences = {}
    for pos in shared:
        fields = [key for key in STATE_KEYS if prefix_states[pos].get(key) != candidate_prefixes[pos].get(key)]
        if fields:
            boundary_differences[str(pos)] = fields
    require(not boundary_differences, f"{arm['name']}: prefix state differs: {boundary_differences}")
    if arm["spec"]:
        require(record["drafts_offered"] > 0 and record["drafts_accepted"] > 0,
                f"{arm['name']}: no accepted draft")
    review["checks"].append({"arm": arm["name"], "tokens_equal": True,
                             "final_state_equal": True, "shared_boundaries": shared,
                             "boundaries_equal": True,
                             "drafts_offered": record.get("drafts_offered", 0),
                             "drafts_accepted": record.get("drafts_accepted", 0)})

samples = [json.loads(line) for line in (SUPERVISOR / "memory.jsonl").read_text().splitlines()]
require(len(samples) == 376, f"unexpected supervisor sample count {len(samples)}")
scope_rows = [cg for row in samples for cg in row["cgroups"] if cg["path"].endswith(".scope")]
require(scope_rows, "missing scope cgroup samples")
events = {key: max(cg["memory_events"].get(key, 0) for cg in scope_rows)
          for key in ("low", "high", "max", "oom", "oom_kill")}
require(not any(events.values()), f"cgroup memory events observed: {events}")
minimum_available = min(row["available_bytes"] for row in samples)
minimum_admission = min(row["admission_available_bytes"] for row in samples)
require(minimum_available >= 6 * 1024**3, "six-GiB host floor breached")
require(minimum_admission >= 6 * 1024**3, "six-GiB admission floor breached")
review["supervisor"] = {"sample_count": len(samples),
                        "minimum_available_bytes": minimum_available,
                        "minimum_admission_available_bytes": minimum_admission,
                        "cgroup_event_maxima": events}
(ROOT / "verification.json").write_text(json.dumps(review, indent=2) + "\n")
print(json.dumps(review, indent=2))
