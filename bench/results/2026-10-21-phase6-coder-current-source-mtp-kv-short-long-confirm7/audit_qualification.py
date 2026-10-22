#!/usr/bin/env python3
"""Check exact responses and per-arm memory supervision for this campaign."""
import argparse
import json
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-answer", default=(
        "EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, "
        "LATE=TIDAL-COPPER-529, SUM=1692"))
    parser.add_argument("--output", type=Path, default=here / "qualification-audit.json")
    args = parser.parse_args()

    campaign = json.loads((here / "campaign/campaign.json").read_text())
    expected_arms = (campaign["blocks"] * len(campaign["kv_formats"]) *
                     len(campaign["mtp_windows"]) * len(campaign["workloads"]))
    rows, errors = [], []
    min_host = float("inf")
    min_admission = float("inf")
    event_max = {name: 0 for name in ("low", "high", "max", "oom", "oom_kill")}
    expected_scope_max = 28 * 1024**3

    for run in campaign["runs"]:
        arm = here / "campaign" / run["directory"]
        requests = json.loads((arm / "requests.json").read_text())
        supervisor = json.loads((arm / "supervisor/result.json").read_text())
        measured = [item for item in requests.get("checks", []) if not item.get("warmup")]
        content = ""
        request_status = None
        if len(measured) == 1:
            item = measured[0]
            request_status = item.get("status")
            content = "".join(choice.get("message", {}).get("content", "")
                              for choice in item.get("response", {}).get("choices", []))
            if request_status != "pass":
                errors.append({"run": run["name"], "error": "request status", "observed": request_status})
            if args.expected_answer not in content:
                errors.append({"run": run["name"], "error": "exact answer mismatch", "observed": content})
        else:
            errors.append({"run": run["name"], "error": "measured request count", "observed": len(measured)})
        if supervisor.get("status") != "pass":
            errors.append({"run": run["name"], "error": "supervisor status", "observed": supervisor.get("status")})

        host = supervisor.get("minimum_available_bytes", 0)
        admission = supervisor.get("minimum_admission_available_bytes", 0)
        min_host = min(min_host, host / 1024**3)
        min_admission = min(min_admission, admission / 1024**3)
        if host < 6 * 1024**3:
            errors.append({"run": run["name"], "error": "six-GiB host floor breached", "observed_gib": host / 1024**3})

        samples = [json.loads(line) for line in (arm / "supervisor/memory.jsonl").read_text().splitlines()]
        if not samples:
            errors.append({"run": run["name"], "error": "no memory samples"})
        seen_scope_max = False
        for sample in samples:
            if not sample.get("cgroup_v2_observed"):
                errors.append({"run": run["name"], "error": "cgroup v2 not observed"})
                break
            for cgroup in sample.get("cgroups", []):
                if cgroup.get("max_bytes") == expected_scope_max:
                    seen_scope_max = True
                for name, value in cgroup.get("memory_events", {}).items():
                    event_max[name] = max(event_max.get(name, 0), value)
        if not seen_scope_max:
            errors.append({"run": run["name"], "error": "28-GiB per-arm cgroup limit missing"})
        for name in ("high", "max", "oom", "oom_kill"):
            if event_max.get(name, 0):
                errors.append({"run": run["name"], "error": f"cgroup {name} event", "observed": event_max[name]})

        rows.append({"run": run["name"], "block": run["block"], "kv": run["kv"],
                     "mtp_window": run["window"], "request_status": request_status,
                     "exact_answer": args.expected_answer in content,
                     "prompt_tokens": run["metrics"].get("prompt_tokens"),
                     "completion_tokens": run["metrics"].get("completion_tokens"),
                     "minimum_host_available_gib": host / 1024**3,
                     "minimum_admission_available_gib": admission / 1024**3,
                     "supervisor_status": supervisor.get("status"),
                     "memory_samples": len(samples)})

    result = {"schema": 1, "campaign": "campaign/campaign.json",
              "expected_exact_answer": args.expected_answer, "arms": rows,
              "arm_count": len(rows),
              "exact_answer_pass_count": sum(row["exact_answer"] for row in rows),
              "minimum_host_available_gib": min_host,
              "minimum_admission_available_gib": min_admission,
              "maximum_cgroup_memory_events": event_max, "errors": errors,
              "expected_arm_count": expected_arms,
              "passed": (not errors and len(rows) == expected_arms and
                         all(row["exact_answer"] for row in rows))}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "arm_count", "expected_arm_count", "exact_answer_pass_count", "minimum_host_available_gib",
        "minimum_admission_available_gib", "maximum_cgroup_memory_events", "passed", "errors")}, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
