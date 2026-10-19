#!/usr/bin/env python3
"""Independently review the pinned-control/current-candidate rollback smoke."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
ARMS = ("control", "candidate")


def review_arm(arm):
    directory = ROOT / arm
    result = json.loads((directory / "result.json").read_text())
    stdout = (directory / "stdout.txt").read_text()
    output_ids = [int(value) for value in re.findall(r"^output\s*:\s*(\d+)\s*$", stdout, re.M)]
    assert result["status"] == "pass", (arm, result["status"])
    assert result["returncode"] == 0, (arm, result["returncode"])
    assert len(output_ids) == 1, (arm, output_ids)
    assert result["minimum_available_bytes"] >= 6 * 1024**3, arm

    events = []
    samples = [json.loads(line) for line in (directory / "memory.jsonl").read_text().splitlines()]
    for sample in samples:
        for cgroup in sample.get("cgroups", []):
            events.extend(cgroup.get("memory_events", {}).values())
    assert events and all(value == 0 for value in events), arm
    binary = Path(result["command"][0])
    return {
        "status": result["status"],
        "returncode": result["returncode"],
        "engine_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "output_token_ids": output_ids,
        "minimum_available_bytes": result["minimum_available_bytes"],
        "minimum_admission_available_bytes": result["minimum_admission_available_bytes"],
        "memory_samples": len(samples),
        "cgroup_events_all_zero": True,
    }, result["command"]


reviewed = {arm: review_arm(arm) for arm in ARMS}
assert reviewed["control"][1][1:] == reviewed["candidate"][1][1:]
assert reviewed["control"][0]["output_token_ids"] == reviewed["candidate"][0]["output_token_ids"]
analysis = {
    "schema_version": 1,
    "comparison": "functional rollback smoke only; no performance inference",
    "same_command_except_executable": True,
    "same_output_token_ids": True,
    "arms": {arm: reviewed[arm][0] for arm in ARMS},
}
(ROOT / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
print(json.dumps(analysis, indent=2))
