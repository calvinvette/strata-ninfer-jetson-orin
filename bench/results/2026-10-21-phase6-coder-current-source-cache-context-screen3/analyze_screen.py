#!/usr/bin/env python3
"""Qualify and summarize the randomized Coder cache × context screen."""
import json
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "campaign/campaign.json"
EXPECTED = (
    "EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, "
    "LATE=TIDAL-COPPER-529, SUM=1692"
)
GIB = 1024**3


def median(values):
    return statistics.median(values) if values else None


def main():
    campaign = json.loads(CAMPAIGN.read_text())
    errors, cells = [], []
    minimum_host = float("inf")
    minimum_admission = float("inf")
    event_max = {name: 0 for name in ("low", "high", "max", "oom", "oom_kill")}

    for cell in campaign["cells"]:
        arm = HERE / "campaign" / cell["name"]
        request_file = json.loads((arm / "requests.json").read_text())
        capability = json.loads((arm / "capabilities.json").read_text())
        supervisor = json.loads((arm / "supervisor/result.json").read_text())
        measured = [row for row in request_file.get("checks", []) if not row.get("warmup")]
        if cell.get("status") != "pass" or supervisor.get("status") != "pass":
            errors.append({"cell": cell["name"], "error": "campaign or supervisor did not pass"})
        if len(measured) != campaign["rounds_per_cell"]:
            errors.append({"cell": cell["name"], "error": "measured repetition count",
                           "observed": len(measured)})

        ttft, total, prompt_rate, decode_rate = [], [], [], []
        for row in measured:
            response = row.get("response", {})
            content = "".join(choice.get("message", {}).get("content", "")
                              for choice in response.get("choices", []))
            usage = response.get("usage", {})
            timings = response.get("timings", {})
            if row.get("status") != "pass" or EXPECTED not in content:
                errors.append({"cell": cell["name"], "round": row.get("round"),
                               "error": "request or exact-answer check failed"})
            if usage.get("prompt_tokens") != 512 or usage.get("completion_tokens") != 45:
                errors.append({"cell": cell["name"], "round": row.get("round"),
                               "error": "actual token count mismatch", "usage": usage})
            stream = row.get("stream_observation", {})
            if stream.get("first_visible_delta_s") is not None:
                ttft.append(stream["first_visible_delta_s"])
            if row.get("client_elapsed_s") is not None:
                total.append(row["client_elapsed_s"])
            if timings.get("prompt_per_second") is not None:
                prompt_rate.append(timings["prompt_per_second"])
            if timings.get("predicted_per_second") is not None:
                decode_rate.append(timings["predicted_per_second"])

        minimum_host = min(minimum_host, supervisor.get("minimum_available_bytes", 0) / GIB)
        minimum_admission = min(minimum_admission,
                                supervisor.get("minimum_admission_available_bytes", 0) / GIB)
        if supervisor.get("minimum_available_bytes", 0) < 6 * GIB:
            errors.append({"cell": cell["name"], "error": "six-GiB host floor breached"})

        memory_samples = [json.loads(line) for line in
                          (arm / "supervisor/memory.jsonl").read_text().splitlines()
                          if line.strip()]
        if not memory_samples:
            errors.append({"cell": cell["name"], "error": "missing memory samples"})
        scope_limit_seen = False
        arm_events = {name: 0 for name in event_max}
        for sample in memory_samples:
            if not sample.get("cgroup_v2_observed"):
                errors.append({"cell": cell["name"], "error": "cgroup v2 not observed"})
            for cg in sample.get("cgroups", []):
                if cg.get("max_bytes") == 28 * GIB:
                    scope_limit_seen = True
                for name, value in cg.get("memory_events", {}).items():
                    if name in arm_events and isinstance(value, int):
                        arm_events[name] = max(arm_events[name], value)
        if not scope_limit_seen:
            errors.append({"cell": cell["name"], "error": "28-GiB cgroup limit not observed"})
        for name in event_max:
            event_max[name] = max(event_max[name], arm_events[name])
        for name in ("high", "max", "oom", "oom_kill"):
            if arm_events[name]:
                errors.append({"cell": cell["name"], "error": f"cgroup {name} event",
                               "observed": arm_events[name]})

        engine = capability.get("engine", {})
        cells.append({
            "name": cell["name"], "order": cell["order"],
            "cache_budget_mib": cell["expert_cache_argument"],
            "context_tokens": cell["context_tokens"],
            "request_count": len(measured), "exact_answer_pass_count": sum(
                row.get("status") == "pass" and EXPECTED in "".join(
                    choice.get("message", {}).get("content", "")
                    for choice in row.get("response", {}).get("choices", []))
                for row in measured),
            "median_client_ttft_s": median(ttft),
            "median_client_total_s": median(total),
            "median_prompt_tokens_per_s": median(prompt_rate),
            "median_decode_tokens_per_s": median(decode_rate),
            "actual_expert_slots": engine.get("expert_slots"),
            "actual_expert_cache_mib": engine.get("expert_cache_mib"),
            "minimum_host_available_gib": supervisor.get("minimum_available_bytes", 0) / GIB,
            "minimum_admission_available_gib":
                supervisor.get("minimum_admission_available_bytes", 0) / GIB,
            "memory_samples": len(memory_samples),
            "maximum_cgroup_memory_events": arm_events,
            "supervisor_status": supervisor.get("status"),
        })

    by_key = {(cell["cache_budget_mib"], cell["context_tokens"]): cell for cell in cells}
    contrasts = []
    for metric in ("median_client_ttft_s", "median_client_total_s",
                   "median_prompt_tokens_per_s", "median_decode_tokens_per_s"):
        for context in campaign["context_values"]:
            low, high = by_key[(min(campaign["cache_values"]), context)][metric], \
                        by_key[(max(campaign["cache_values"]), context)][metric]
            contrasts.append({"factor": "cache budget", "metric": metric,
                              "context_tokens": context,
                              "low_cache_value": min(campaign["cache_values"]),
                              "high_cache_value": max(campaign["cache_values"]),
                              "change_percent": (high / low - 1) * 100})
        for cache in campaign["cache_values"]:
            low, high = by_key[(cache, min(campaign["context_values"]))][metric], \
                        by_key[(cache, max(campaign["context_values"]))][metric]
            contrasts.append({"factor": "configured context", "metric": metric,
                              "cache_budget_mib": cache,
                              "low_context_value": min(campaign["context_values"]),
                              "high_context_value": max(campaign["context_values"]),
                              "change_percent": (high / low - 1) * 100})

    output = {"schema": 1, "campaign": "campaign/campaign.json",
              "scope": "three same-process screening requests per cell; descriptive medians, no confidence intervals",
              "expected_answer": EXPECTED, "cells": cells, "contrasts": contrasts,
              "memory_sample_count": sum(cell["memory_samples"] for cell in cells),
              "minimum_host_available_gib": minimum_host,
              "minimum_admission_available_gib": minimum_admission,
              "maximum_cgroup_memory_events": event_max,
              "energy": "not measured",
              "errors": errors,
              "passed": (campaign.get("finished_wall_time_s") is not None and not errors and
                         len(cells) == campaign["planned_cells"])}
    (HERE / "analysis.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in (
        "cells", "contrasts", "memory_sample_count", "minimum_host_available_gib",
        "minimum_admission_available_gib", "maximum_cgroup_memory_events", "passed", "errors")},
        indent=2))
    if not output["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
