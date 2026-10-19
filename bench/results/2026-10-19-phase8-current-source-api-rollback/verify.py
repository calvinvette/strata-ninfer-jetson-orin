#!/usr/bin/env python3
"""Independent paired review of pinned-control and candidate API rollback runs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = ("repeated_greedy_0", "repeated_greedy_1", "repeated_greedy_2",
         "openai_stream", "anthropic_stream", "cancel_decode", "cancel_prefill")
EXPECTED = "Hello Orin!"


def require(ok, msg):
    if not ok:
        raise SystemExit(msg)


def response_text(row):
    if "text" in row:
        return row["text"].strip()
    response = row.get("response") or {}
    return response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


arms = {}
for name in ("control", "candidate"):
    root = ROOT / name
    result = json.loads((root / "result.json").read_text())
    protocol = json.loads((root / "protocol.json").read_text())
    review = json.loads((root / "independent-review.json").read_text())
    require(result.get("status") == "pass", f"{name}: runner failed")
    require(review.get("overall_pass") is True, f"{name}: protocol review failed")
    by_name = {row["check"]: row for row in protocol["checks"]}
    require(set(NAMES) <= by_name.keys(), f"{name}: missing protocol scenario")
    for check in NAMES:
        row = by_name[check]
        require(row.get("status") == "pass", f"{name}/{check}: did not pass")
        if check in ("openai_stream", "anthropic_stream"):
            actual = row.get("text", "").strip()
        elif check.startswith("cancel_"):
            actual = response_text(row.get("recovery", {}))
        else:
            actual = response_text(row)
        require(actual == EXPECTED, f"{name}/{check}: unexpected output {actual!r}")
        if check.startswith("cancel_"):
            require(response_text(row.get("recovery", {})) == EXPECTED,
                    f"{name}/{check}: same-service recovery did not match")
    arms[name] = {"by_name": by_name}

for name in NAMES:
    left, right = (arms[arm]["by_name"][name] for arm in ("control", "candidate"))
    left_text = left.get("text", "").strip() if name in ("openai_stream", "anthropic_stream") else response_text(left)
    right_text = right.get("text", "").strip() if name in ("openai_stream", "anthropic_stream") else response_text(right)
    require(left_text == right_text, f"{name}: arm response differs")
    if name.startswith("cancel_"):
        require(response_text(left["recovery"]) == response_text(right["recovery"]),
                f"{name}: recovery response differs")

config_control = json.loads((ROOT / "control-config.json").read_text())
config_candidate = json.loads((ROOT / "candidate-config.json").read_text())
for key in set(config_control) | set(config_candidate):
    if key == "exe":
        continue
    require(config_control.get(key) == config_candidate.get(key), f"configs differ at {key}")

supervisors = {}
for name, path_name in (("control", "supervisor-control-retry"),
                        ("candidate", "supervisor-candidate")):
    folder = ROOT / path_name
    summary = json.loads((folder / "result.json").read_text())
    rows = [json.loads(line) for line in (folder / "memory.jsonl").read_text().splitlines()]
    scope = [cg for row in rows for cg in row["cgroups"] if cg["path"].endswith(".scope")]
    require(summary.get("status") == "pass", f"{name}: supervisor failed")
    require(len(rows) >= 10, f"{name}: too few telemetry samples")
    events = {key: max(cg["memory_events"].get(key, 0) for cg in scope)
              for key in ("low", "high", "max", "oom", "oom_kill")}
    require(not any(events.values()), f"{name}: cgroup memory events {events}")
    require(summary["minimum_available_bytes"] >= 6 * 1024**3, f"{name}: host floor breached")
    require(summary["minimum_admission_available_bytes"] >= 6 * 1024**3,
            f"{name}: admission floor breached")
    supervisors[name] = {"samples": len(rows),
                         "minimum_available_bytes": summary["minimum_available_bytes"],
                         "minimum_admission_available_bytes": summary["minimum_admission_available_bytes"],
                         "cgroup_event_maxima": events,
                         "elapsed_s": summary["elapsed_s"]}

report = {"passed": True, "scenarios": list(NAMES),
          "expected_response": EXPECTED, "arms": supervisors,
          "same_config_except_executable": True,
          "active_prefill_progress_proven": False}
(ROOT / "paired-review.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
