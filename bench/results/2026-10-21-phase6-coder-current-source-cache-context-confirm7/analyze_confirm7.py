#!/usr/bin/env python3
"""Validate and summarize paired current-source Coder cache confirmation."""
import json
import random
import statistics
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_ROOT = ROOT / "per-cell-scopes"
EXPECTED = (
    "EARLY=TUNDRA-ORBIT-593, MIDDLE=COBALT-MAPLE-248, "
    "LATE=GRANITE-COMET-761, SUM=1602"
)
CACHE = (1500, 3000)
GIB = 1024**3


def percentile_interval(values, seed, draws=100000):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values)))
                     for _ in range(draws))
    return [samples[int(0.025 * draws)], samples[int(0.975 * draws)]]


def paired_effect(label, low_rows, high_rows, metric, seed):
    effects = [100 * (high_rows[block][metric] / low_rows[block][metric] - 1)
               for block in sorted(low_rows)]
    return {"contrast": label, "metric": metric,
            "paired_block_effect_percent": effects,
            "median_effect_percent": statistics.median(effects),
            "paired_block_bootstrap_95_interval_percent":
                percentile_interval(effects, seed)}


def main():
    design = json.loads((ROOT / "design.json").read_text())
    blocks = sorted(RUN_ROOT.glob("block-*/campaign.json"))
    errors, rows = [], []
    per_cache = {cache: {} for cache in CACHE}
    min_host = float("inf")
    min_admission = float("inf")
    event_max = {name: 0 for name in ("low", "high", "max", "oom", "oom_kill")}
    slots_by_cache = {cache: set() for cache in CACHE}
    cache_mib_by_cache = {cache: set() for cache in CACHE}
    local_dates = set()

    for campaign_path in blocks:
        block_name = campaign_path.parent.name
        campaign = json.loads(campaign_path.read_text())
        if campaign.get("rounds_per_cell") != 3 or len(campaign.get("cells", [])) != 2:
            errors.append({"block": block_name, "error": "expected 2 cells x 3 requests"})
        block_rows = {cache: {} for cache in CACHE}
        for cell in campaign.get("cells", []):
            cache = int(cell["expert_cache_argument"])
            if cache not in CACHE or int(cell["context_tokens"]) != 8192:
                errors.append({"block": block_name, "cell": cell.get("name"),
                               "error": "unexpected factor value"})
                continue
            arm = campaign_path.parent / cell["name"]
            requests = json.loads((arm / "requests.json").read_text())
            capability = json.loads((arm / "capabilities.json").read_text()).get("engine", {})
            supervisor = json.loads((arm / "supervisor/result.json").read_text())
            measured = [row for row in requests.get("checks", []) if not row.get("warmup")]
            if cell.get("status") != "pass" or supervisor.get("status") != "pass":
                errors.append({"block": block_name, "cell": cell["name"],
                               "error": "cell or supervisor did not pass"})
            if len(measured) != 3:
                errors.append({"block": block_name, "cell": cell["name"],
                               "error": "measured repetition count", "observed": len(measured)})

            request_metrics = {key: [] for key in (
                "client_ttft_s", "client_total_s", "prompt_tps", "decode_tps")}
            for item in measured:
                if item.get("wall_time_s") is not None:
                    local_dates.add(datetime.fromtimestamp(item["wall_time_s"]).date().isoformat())
                response = item.get("response", {})
                text = "".join(choice.get("message", {}).get("content", "")
                               for choice in response.get("choices", []))
                usage, timings = response.get("usage", {}), response.get("timings", {})
                if item.get("status") != "pass" or text.strip() != EXPECTED:
                    errors.append({"block": block_name, "cell": cell["name"],
                                   "round": item.get("round"), "error": "exact answer/request failed",
                                   "answer": text})
                if usage.get("prompt_tokens") != 512 or timings.get("prompt_n") != 512:
                    errors.append({"block": block_name, "cell": cell["name"],
                                   "round": item.get("round"), "error": "actual prompt tokens not 512"})
                if timings.get("predicted_n") != 47:
                    errors.append({"block": block_name, "cell": cell["name"],
                                   "round": item.get("round"), "error": "answer token count mismatch",
                                   "observed": timings.get("predicted_n")})
                stream = item.get("stream_observation", {})
                request_metrics["client_ttft_s"].append(stream.get("first_visible_delta_s"))
                request_metrics["client_total_s"].append(item.get("client_elapsed_s"))
                request_metrics["prompt_tps"].append(timings.get("prompt_per_second"))
                request_metrics["decode_tps"].append(timings.get("predicted_per_second"))

            summary = {key: statistics.median(values) for key, values in request_metrics.items()}
            block_rows[cache] = summary
            per_cache[cache][block_name] = summary
            min_host = min(min_host, supervisor.get("minimum_available_bytes", 0) / GIB)
            min_admission = min(min_admission,
                                supervisor.get("minimum_admission_available_bytes", 0) / GIB)
            if supervisor.get("minimum_available_bytes", 0) < 6 * GIB:
                errors.append({"block": block_name, "cell": cell["name"],
                               "error": "six-GiB host floor breached"})

            samples = [json.loads(line) for line in
                       (arm / "supervisor/memory.jsonl").read_text().splitlines()
                       if line.strip()]
            arm_events = {name: 0 for name in event_max}
            saw_limit = False
            for sample in samples:
                if not sample.get("cgroup_v2_observed"):
                    errors.append({"block": block_name, "cell": cell["name"],
                                   "error": "cgroup v2 not observed"})
                for cg in sample.get("cgroups", []):
                    if cg.get("max_bytes") == 28 * GIB:
                        saw_limit = True
                    for name, value in cg.get("memory_events", {}).items():
                        if name in arm_events and isinstance(value, int):
                            arm_events[name] = max(arm_events[name], value)
            if not saw_limit:
                errors.append({"block": block_name, "cell": cell["name"],
                               "error": "28-GiB cgroup limit missing"})
            for name, value in arm_events.items():
                event_max[name] = max(event_max[name], value)
                if name in ("high", "max", "oom", "oom_kill") and value:
                    errors.append({"block": block_name, "cell": cell["name"],
                                   "error": f"cgroup {name} event", "observed": value})
            if (capability.get("max_context") != 8192 or capability.get("kv") != "fp16" or
                    capability.get("mtp_max") != 0 or capability.get("pool_workers") != 8 or
                    capability.get("conversation_cache_mib") != 0):
                errors.append({"block": block_name, "cell": cell["name"],
                               "error": "fixed profile mismatch", "engine": capability})
            if capability.get("expert_slots", 0) <= 0:
                errors.append({"block": block_name, "cell": cell["name"],
                               "error": "no expert cache admitted"})
            slots_by_cache[cache].add(capability.get("expert_slots"))
            cache_mib_by_cache[cache].add(capability.get("expert_cache_mib"))

            rows.append({"block": block_name, "cell": cell["name"],
                         "cache_argument_mib": cache, "context_tokens": 8192,
                         "actual_expert_slots": capability.get("expert_slots"),
                         "actual_expert_cache_mib": capability.get("expert_cache_mib"),
                         "request_count": len(measured), "request_medians": summary,
                         "minimum_host_available_gib": supervisor.get("minimum_available_bytes", 0) / GIB,
                         "minimum_admission_available_gib":
                             supervisor.get("minimum_admission_available_bytes", 0) / GIB,
                         "memory_samples": len(samples), "maximum_cgroup_memory_events": arm_events})

        if all(block_rows[cache] for cache in CACHE):
            if block_rows[CACHE[0]]["client_ttft_s"] <= 0:
                errors.append({"block": block_name, "error": "invalid paired response"})

    if len(blocks) != 7 or any(len(per_cache[cache]) != 7 for cache in CACHE):
        errors.append({"error": "expected seven complete paired blocks",
                       "blocks": len(blocks),
                       "cache_cell_counts": {str(k): len(v) for k, v in per_cache.items()}})
    for cache in CACHE:
        if len(slots_by_cache[cache]) != 1 or len(cache_mib_by_cache[cache]) != 1:
            errors.append({"error": "actual cache allocation varied across blocks",
                           "cache_argument_mib": cache,
                           "expert_slots": sorted(x for x in slots_by_cache[cache] if x is not None),
                           "expert_cache_mib": sorted(x for x in cache_mib_by_cache[cache] if x is not None)})
    if len(local_dates) != 1:
        errors.append({"error": "confirmation arms did not all run on one local calendar day",
                       "dates": sorted(local_dates)})
    contrasts = [paired_effect(f"cache 3000 vs 1500 at 8K: {metric}",
                               per_cache[1500], per_cache[3000], metric, 2026102200 + i)
                 for i, metric in enumerate(("client_ttft_s", "client_total_s",
                                             "prompt_tps", "decode_tps"))]
    result = {"schema": 1, "design": "design.json", "blocks": [x.parent.name for x in blocks],
              "cell_rows": rows, "contrasts": contrasts,
              "validation": {"cell_count": len(rows), "measured_request_count":
                             sum(row["request_count"] for row in rows),
                             "local_dates": sorted(local_dates),
                             "actual_slots_by_cache_argument":
                                 {str(cache): sorted(slots_by_cache[cache]) for cache in CACHE},
                             "actual_cache_mib_by_cache_argument":
                                 {str(cache): sorted(cache_mib_by_cache[cache]) for cache in CACHE},
                             "minimum_host_available_gib": min_host,
                             "minimum_admission_available_gib": min_admission,
                             "maximum_cgroup_memory_events": event_max,
                             "energy": "not measured", "errors": errors,
                             "passed": not errors and len(blocks) == 7 and len(rows) == 14}}
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"validation": result["validation"], "contrasts": contrasts}, indent=2))
    if not result["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
