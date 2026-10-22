#!/usr/bin/env python3
"""Audit seven paired, long-prompt cache confirmation blocks."""
import hashlib
import json
import random
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "per-cell-scopes"
GIB = 1024**3
EXPECTED = (
    "EARLY=ALPINE-HARBOR-284, MIDDLE=COBALT-MAPLE-571, "
    "LATE=VIOLET-COMET-638, SUM=1493"
)
CACHES = (1500, 3000)
METRICS = ("client_ttft_s", "client_total_s", "prompt_tps", "decode_tps")
EXPECTED_PROFILE = {
    "max_context": 16384,
    "kv": "fp16",
    "mtp_max": 0,
    "pool_workers": 8,
    "conversation_cache_mib": 0,
}


def percentile_interval(values, seed=2026102121, draws=100000):
    rng = random.Random(seed)
    samples = sorted(
        statistics.median(rng.choices(values, k=len(values)))
        for _ in range(draws)
    )
    return [samples[int(0.025 * draws)], samples[int(0.975 * draws)]]


def response_text(item):
    return "".join(
        choice.get("message", {}).get("content", "")
        for choice in item.get("response", {}).get("choices", [])
    ).strip()


def request_date(item):
    wall_time = item.get("wall_time_s")
    return datetime.fromtimestamp(wall_time).date().isoformat() if wall_time else None


def clock_summary(samples, errors, label):
    gpu_hz, cpu_hz, emc_statuses = [], [], {}
    for sample in samples:
        obs = sample.get("clock_observations")
        if not isinstance(obs, dict):
            errors.append({"cell": label, "error": "clock sample missing"})
            continue
        gpu = obs.get("gpu", {})
        if isinstance(gpu.get("hz"), int):
            gpu_hz.append(gpu["hz"])
        else:
            errors.append({"cell": label, "error": "GPU clock value missing"})
        for value in obs.get("cpu", {}).values():
            if isinstance(value, dict) and isinstance(value.get("hz"), int):
                cpu_hz.append(value["hz"])
        emc = obs.get("emc", {})
        status = emc.get("status", "observed" if isinstance(emc.get("hz"), int) else "missing")
        emc_statuses[status] = emc_statuses.get(status, 0) + 1
    def stats(values):
        if not values:
            return None
        return {"min_hz": min(values), "median_hz": statistics.median(values), "max_hz": max(values)}
    return {"gpu_hz": stats(gpu_hz), "cpu_per_core_sample_hz": stats(cpu_hz),
            "emc_observation_status_counts": emc_statuses,
            "samples_with_gpu_clock": len(gpu_hz), "samples_with_cpu_clocks": len(cpu_hz)}


def main():
    errors, rows = [], []
    design = json.loads((ROOT / "design.json").read_text())
    for filename, key in (("config.json", "config_sha256"), ("workloads.json", "workloads_sha256")):
        actual = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        if actual != design.get(key):
            errors.append({"error": f"{filename} checksum mismatch", "expected": design.get(key), "observed": actual})
    model_hashes = {}
    for line in (ROOT / "model-sha256.txt").read_text().splitlines():
        digest, path = line.split(None, 1)
        model_hashes[path] = digest
    if model_hashes != design.get("model_files_sha256"):
        errors.append({"error": "model shard checksum manifest mismatch"})
    by_cache = {cache: {} for cache in CACHES}
    slots_by_cache = {cache: set() for cache in CACHES}
    allocation_by_cache = {cache: set() for cache in CACHES}
    min_host = min_admission = float("inf")
    event_max = {name: 0 for name in ("low", "high", "max", "oom", "oom_kill")}
    block_dates = {}

    for block_n in range(1, 8):
        block_dir = RUNS / f"block-{block_n:02d}"
        campaign_path = block_dir / "campaign.json"
        if not campaign_path.exists():
            errors.append({"block": block_n, "error": "campaign record missing"})
            continue
        campaign = json.loads(campaign_path.read_text())
        cells = campaign.get("cells", [])
        if campaign.get("rounds_per_cell") != 3 or len(cells) != 2:
            errors.append({"block": block_n, "error": "expected paired cells with three measured requests"})
        if campaign.get("trace_enabled") is not False:
            errors.append({"block": block_n, "error": "trace must be disabled for timing"})
        if not campaign.get("sample_clocks") and campaign.get("clock_sampling") is False:
            errors.append({"block": block_n, "error": "read-only clock sampling was disabled"})
        order_values = {cell.get("order") for cell in cells}
        if order_values != {0, 1}:
            errors.append({"block": block_n, "error": "paired cache order was not recorded"})

        block_dates[block_n] = {}
        block_results = {}
        for cell in cells:
            cache = int(cell.get("expert_cache_argument", -1))
            name = cell.get("name", "unknown")
            arm = block_dir / name
            if cache not in CACHES or int(cell.get("context_tokens", -1)) != 16384:
                errors.append({"block": block_n, "cell": name, "error": "factor mismatch"})
                continue
            try:
                req = json.loads((arm / "requests.json").read_text())
                cap = json.loads((arm / "capabilities.json").read_text()).get("engine", {})
                sup = json.loads((arm / "supervisor/result.json").read_text())
                samples = [json.loads(line) for line in (arm / "supervisor/memory.jsonl").read_text().splitlines() if line.strip()]
            except (OSError, json.JSONDecodeError) as exc:
                errors.append({"block": block_n, "cell": name, "error": f"missing or invalid cell evidence: {exc}"})
                continue

            measured = [item for item in req.get("checks", []) if not item.get("warmup")]
            warmups = [item for item in req.get("checks", []) if item.get("warmup")]
            if len(measured) != 3 or len(warmups) != 1 or cell.get("status") != "pass" or sup.get("status") != "pass":
                errors.append({"block": block_n, "cell": name, "error": "cell status or request count failure",
                               "measured": len(measured), "warmups": len(warmups)})
            request_metrics = {metric: [] for metric in METRICS}
            dates = set()
            for item in warmups + measured:
                content = response_text(item)
                usage = item.get("response", {}).get("usage", {})
                timing = item.get("response", {}).get("timings", {})
                if item.get("status") != "pass" or content != EXPECTED:
                    errors.append({"block": block_n, "cell": name, "warmup": item.get("warmup"),
                                   "error": "exact answer/request check failed", "answer": content})
                if (usage.get("prompt_tokens") != 7501 or usage.get("completion_tokens") != 48 or
                        timing.get("prompt_n") != 7501 or timing.get("predicted_n") != 48):
                    errors.append({"block": block_n, "cell": name, "warmup": item.get("warmup"),
                                   "error": "actual prompt/completion token count mismatch", "usage": usage,
                                   "timings": {k: timing.get(k) for k in ("prompt_n", "predicted_n")}})
                date = request_date(item)
                if date:
                    dates.add(date)
                if item in measured:
                    stream = item.get("stream_observation", {})
                    request_metrics["client_ttft_s"].append(stream.get("first_visible_delta_s"))
                    request_metrics["client_total_s"].append(item.get("client_elapsed_s"))
                    request_metrics["prompt_tps"].append(timing.get("prompt_per_second"))
                    request_metrics["decode_tps"].append(timing.get("predicted_per_second"))
            block_dates[block_n][cache] = dates
            if not dates:
                errors.append({"block": block_n, "cell": name, "error": "request dates missing"})
            if any(not values or any(value is None for value in values) for values in request_metrics.values()):
                errors.append({"block": block_n, "cell": name, "error": "one or more timing metrics missing"})
                medians = {}
            else:
                medians = {metric: statistics.median(values) for metric, values in request_metrics.items()}
            by_cache[cache][block_n] = medians
            block_results[cache] = medians

            for field, expected in EXPECTED_PROFILE.items():
                if cap.get(field) != expected:
                    errors.append({"block": block_n, "cell": name, "error": "fixed runtime profile mismatch",
                                   "field": field, "observed": cap.get(field), "expected": expected})
            if cap.get("expert_slots", 0) <= 0 or cap.get("expert_cache_mib", 0) <= 0:
                errors.append({"block": block_n, "cell": name, "error": "expert cache not admitted"})
            slots_by_cache[cache].add(cap.get("expert_slots"))
            allocation_by_cache[cache].add(cap.get("expert_cache_mib"))

            host = sup.get("minimum_available_bytes", 0) / GIB
            admission = sup.get("minimum_admission_available_bytes", 0) / GIB
            min_host = min(min_host, host)
            min_admission = min(min_admission, admission)
            if host < 6 or admission < 6:
                errors.append({"block": block_n, "cell": name, "error": "six-GiB headroom floor breached"})
            if not samples:
                errors.append({"block": block_n, "cell": name, "error": "memory samples missing"})
            observed_limit = False
            cell_events = {key: 0 for key in event_max}
            for sample in samples:
                if not sample.get("cgroup_v2_observed"):
                    errors.append({"block": block_n, "cell": name, "error": "cgroup v2 not observed"})
                for cgroup in sample.get("cgroups", []):
                    observed_limit |= cgroup.get("max_bytes") == 28 * GIB
                    for key, value in cgroup.get("memory_events", {}).items():
                        if key in cell_events and isinstance(value, int):
                            cell_events[key] = max(cell_events[key], value)
            if not observed_limit:
                errors.append({"block": block_n, "cell": name, "error": "28-GiB scope not observed"})
            for key, value in cell_events.items():
                event_max[key] = max(event_max[key], value)
                if value:
                    errors.append({"block": block_n, "cell": name, "error": f"cgroup {key} event", "count": value})

            clocks = clock_summary(samples, errors, name)
            rows.append({"block": block_n, "cell": name, "cache_budget_mib": cache,
                         "context_tokens": 16384, "request_medians": medians,
                         "expert_slots": cap.get("expert_slots"), "expert_cache_mib": cap.get("expert_cache_mib"),
                         "minimum_host_available_gib": host, "minimum_admission_available_gib": admission,
                         "memory_samples": len(samples), "cgroup_events": cell_events,
                         "request_dates": sorted(dates), "clock_summary": clocks})

        if len(block_dates[block_n]) == 2 and block_dates[block_n][CACHES[0]] != block_dates[block_n][CACHES[1]]:
            errors.append({"block": block_n, "error": "cache arms were not measured on the same local date",
                           "dates_by_cache": {str(k): sorted(v) for k, v in block_dates[block_n].items()}})
        if all(cache in block_results and block_results[cache] for cache in CACHES):
            if block_results[CACHES[0]]["client_ttft_s"] <= 0:
                errors.append({"block": block_n, "error": "invalid paired timing values"})

    effects = {}
    for metric in METRICS:
        raw = [
            100 * (by_cache[3000][block][metric] / by_cache[1500][block][metric] - 1)
            for block in range(1, 8)
            if metric in by_cache[3000].get(block, {}) and metric in by_cache[1500].get(block, {})
        ]
        # Positive is improvement for both latency (lower) and throughput (higher).
        improvement = [-value if metric in ("client_ttft_s", "client_total_s") else value for value in raw]
        effects[metric] = {
            "paired_block_improvement_percent": improvement,
            "median_improvement_percent": statistics.median(improvement) if improvement else None,
            "paired_block_bootstrap_95_interval_percent": percentile_interval(improvement) if improvement else None,
        }
    for cache in CACHES:
        if len(by_cache[cache]) != 7:
            errors.append({"cache_budget_mib": cache, "error": "incomplete seven paired blocks",
                           "complete_blocks": len(by_cache[cache])})
        if len(slots_by_cache[cache] - {None}) != 1 or len(allocation_by_cache[cache] - {None}) != 1:
            errors.append({"cache_budget_mib": cache, "error": "actual expert cache residency varied across cells",
                           "slots": sorted(x for x in slots_by_cache[cache] if x is not None),
                           "allocated_mib": sorted(x for x in allocation_by_cache[cache] if x is not None)})
    out = {
        "scope": "seven paired randomized blocks; each cell median of three measured requests after one exact-answer warmup; held-out 7501-token task at fixed 16384 configured context",
        "expected_answer": EXPECTED,
        "model_source": design.get("model_source"),
        "source_commit": design.get("source_commit"),
        "binary_sha256": design.get("binary_sha256"),
        "model_files_sha256": model_hashes,
        "expected_prompt_tokens": 7501,
        "expected_completion_tokens": 48,
        "effects_3000_vs_1500": effects,
        "rows": rows,
        "expert_slots_by_cache": {str(k): sorted(x for x in slots_by_cache[k] if x is not None) for k in CACHES},
        "expert_cache_mib_by_cache": {str(k): sorted(x for x in allocation_by_cache[k] if x is not None) for k in CACHES},
        "minimum_host_available_gib": min_host,
        "minimum_admission_available_gib": min_admission,
        "maximum_cgroup_events": event_max,
        "energy": "not measured; raw tegrastats rails retained but not process-energy attribution",
        "clock_policy": "read-only dynamic CPU/GPU/EMC samples; no clock controls",
        "errors": errors,
        "passed": len(rows) == 14 and not errors,
    }
    (ROOT / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({key: out[key] for key in (
        "passed", "effects_3000_vs_1500", "minimum_host_available_gib",
        "minimum_admission_available_gib", "maximum_cgroup_events", "errors")}, indent=2))
    if not out["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
