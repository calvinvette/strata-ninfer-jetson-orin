#!/usr/bin/env python3
"""Audit seven-block Coder cache-by-context confirmation and paired effects."""
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools/integration"))
from summarize_controls import interval, metrics

EXPECTED = "EARLY=ALPINE-HARBOR-284, MIDDLE=COBALT-MAPLE-571, LATE=VIOLET-COMET-638, SUM=1493"
design = json.loads((HERE / "design.json").read_text())
errors = []
cells = defaultdict(dict)
min_host = min_admission = None
event_max = {key: 0 for key in ("low", "high", "max", "oom", "oom_kill")}
gpu_clocks, cpu_clocks, tj_temperatures, emc_statuses = [], [], [], defaultdict(int)
block_dates = defaultdict(set)
block_sources = {}

for block in range(1, 8):
    block_dir = HERE / f"per-cell-scopes/block-{block:02d}"
    # Preserve the original seventh block, but replace it in the analysis because
    # that randomized block crossed local midnight and cannot satisfy same-day pairing.
    if block == 7 and (HERE / "per-cell-scopes/block-07-replacement").exists():
        block_dir = HERE / "per-cell-scopes/block-07-replacement"
    block_sources[str(block)] = str(block_dir.relative_to(HERE))
    manifest_path = block_dir / "campaign.json"
    if not manifest_path.exists():
        errors.append(f"missing block {block} manifest")
        continue
    manifest = json.loads(manifest_path.read_text())
    expected_names = {f"cache{cache}-ctx{context}" for cache in (1500, 3000) for context in (8192, 16384)}
    rows = {x.get("name"): x for x in manifest.get("cells", [])}
    if set(rows) != expected_names:
        errors.append(f"block {block}: cell set mismatch: {sorted(rows)}")
        continue
    for cache in (1500, 3000):
        for context in (8192, 16384):
            name = f"cache{cache}-ctx{context}"
            item = rows[name]
            if item.get("expert_cache_argument") != cache or item.get("context_tokens") != context:
                errors.append(f"block {block} {name}: planned factor identity mismatch")
            run = block_dir / name
            request_path = run / "requests.json"
            supervisor_path = run / "supervisor/result.json"
            memory_path = run / "supervisor/memory.jsonl"
            if item.get("status") != "pass" or not all(p.exists() for p in (request_path, supervisor_path, memory_path)):
                errors.append(f"block {block} {name}: failed status or missing output")
                continue
            request_data = json.loads(request_path.read_text())
            warmups = [x for x in request_data.get("checks", []) if x.get("warmup")]
            measured = [x for x in request_data.get("checks", []) if not x.get("warmup")]
            if len(warmups) != 1 or len(measured) != 1:
                errors.append(f"block {block} {name}: expected one warmup and one measured request")
                continue
            row = measured[0]
            response = row.get("response", {})
            usage = response.get("usage", {})
            if row.get("status") != "pass" or response.get("choices", [{}])[0].get("message", {}).get("content") != EXPECTED:
                errors.append(f"block {block} {name}: request or exact answer failed")
            if usage.get("prompt_tokens") != design["expected_prompt_tokens"] or usage.get("completion_tokens") != design["expected_completion_tokens"]:
                errors.append(f"block {block} {name}: token count mismatch {usage}")
            try:
                result_metrics = metrics(row)
            except Exception as exc:
                errors.append(f"block {block} {name}: metrics invalid: {exc}")
                continue
            if result_metrics["drafted"] not in (None, 0) or result_metrics["accepted"] not in (None, 0):
                errors.append(f"block {block} {name}: unexpected speculative token counters")
            cells[block][(cache, context)] = result_metrics
            supervisor = json.loads(supervisor_path.read_text())
            if supervisor.get("status") != "pass" or supervisor.get("returncode") != 0:
                errors.append(f"block {block} {name}: supervisor not clean")
            for key, value in (("host", supervisor.get("minimum_available_bytes")),
                               ("admission", supervisor.get("minimum_admission_available_bytes"))):
                if value is None:
                    errors.append(f"block {block} {name}: missing minimum {key} availability")
                elif key == "host":
                    min_host = value if min_host is None else min(min_host, value)
                else:
                    min_admission = value if min_admission is None else min(min_admission, value)
            samples = [json.loads(line) for line in memory_path.read_text().splitlines() if line.strip()]
            for sample in samples:
                block_dates[block].add(datetime.fromtimestamp(sample["wall_time_s"]).date().isoformat())
                for cg in sample.get("cgroups", []):
                    for key in event_max:
                        event_max[key] = max(event_max[key], cg.get("memory_events", {}).get(key, 0))
                clocks = sample.get("clock_observations", {})
                gpu = clocks.get("gpu", {}).get("hz")
                if isinstance(gpu, (int, float)):
                    gpu_clocks.append(gpu)
                cpu = [x.get("hz") for x in clocks.get("cpu", {}).values() if isinstance(x.get("hz"), (int, float))]
                cpu_clocks.extend(cpu)
                emc = clocks.get("emc", {})
                status = "observed" if isinstance(emc.get("hz"), (int, float)) else emc.get("status", "unavailable")
                emc_statuses[str(status)] += 1
            tegrastats = run / "supervisor/tegrastats.txt"
            if not tegrastats.exists():
                errors.append(f"block {block} {name}: missing tegrastats")
            else:
                for line in tegrastats.read_text(errors="replace").splitlines():
                    match = re.search(r"\btj@([0-9.]+)C", line)
                    if match:
                        tj_temperatures.append(float(match.group(1)))

complete_blocks = [b for b in range(1, 8) if len(cells[b]) == 4]
paired = defaultdict(list)
for metric_name in ("client_total_s", "client_ttft_s", "prompt_tps", "decode_tps"):
    for context in (8192, 16384):
        vals = []
        for block in complete_blocks:
            a, b = cells[block][(1500, context)][metric_name], cells[block][(3000, context)][metric_name]
            vals.append(b / a)
        if vals:
            ci = interval(vals, 2026102130 + context) if len(vals) == 7 else None
            ratio = statistics.median(vals)
            ci_percent = ([(x - 1) * 100 for x in ci] if "tps" in metric_name
                          else [(1 - ci[1]) * 100, (1 - ci[0]) * 100]) if ci else None
            paired[f"cache_effect_{metric_name}_ctx{context}"] = {
                "paired_block_ratios": vals,
                "median_change_percent": ((ratio - 1) * 100 if "tps" in metric_name else (1 - ratio) * 100),
                "paired_block_bootstrap_95_interval_percent": ci_percent,
                "ratio_definition": "candidate/baseline; seconds are reported as latency reduction, throughput as increase",
            }
    for cache in (1500, 3000):
        vals = []
        for block in complete_blocks:
            a, b = cells[block][(cache, 8192)][metric_name], cells[block][(cache, 16384)][metric_name]
            vals.append(b / a)
        if vals:
            ci = interval(vals, 2026102150 + cache) if len(vals) == 7 else None
            paired[f"context_effect_{metric_name}_cache{cache}"] = {
                "paired_block_ratios": vals,
                "median_change_percent": (statistics.median(vals) - 1) * 100,
                "paired_block_bootstrap_95_interval_percent": [(ci[0] - 1) * 100, (ci[1] - 1) * 100] if ci else None,
                "ratio_definition": "16K/8K; seconds are reported as latency increase and throughput as increase",
            }
    # Context interaction compares the 16K-vs-8K latency ratio at cache 3000
    # with that same ratio at cache 1500. It is a block-level ratio of ratios.
    interaction = []
    for block in complete_blocks:
        c1500 = cells[block][(1500, 16384)][metric_name] / cells[block][(1500, 8192)][metric_name]
        c3000 = cells[block][(3000, 16384)][metric_name] / cells[block][(3000, 8192)][metric_name]
        interaction.append(c3000 / c1500)
    if interaction:
        ci = interval(interaction, 2026102140) if len(interaction) == 7 else None
        paired[f"cache_by_context_interaction_{metric_name}"] = {
            "paired_block_ratio_of_ratios": interaction,
            "median_interaction_percent": (statistics.median(interaction) - 1) * 100,
            "paired_block_bootstrap_95_interval_percent": [(ci[0] - 1) * 100, (ci[1] - 1) * 100] if ci else None,
            "interpretation": "for seconds, below zero means the cache latency benefit is larger at 16K; for throughput, below zero means 16K context penalty is more reduced at 3000 MiB",
        }

cfg_hash = hashlib.sha256((HERE / "config.json").read_bytes()).hexdigest()
work_hash = hashlib.sha256((HERE / "workloads.json").read_bytes()).hexdigest()
if cfg_hash != design["config_sha256"]:
    errors.append("base config SHA256 mismatch")
if work_hash != design["workloads_sha256"]:
    errors.append("workloads SHA256 mismatch")
base_config = json.loads((HERE / "config.json").read_text())
binary_path = Path(base_config["exe"])
if not binary_path.exists() or hashlib.sha256(binary_path.read_bytes()).hexdigest() != design["binary_sha256"]:
    errors.append("runtime binary SHA256 mismatch")
if len(complete_blocks) != 7:
    errors.append(f"only {len(complete_blocks)}/7 blocks complete")
for block, dates in block_dates.items():
    if len(dates) != 1:
        errors.append(f"block {block} crossed local dates: {sorted(dates)}")
if min_host is None or min_host < design["host_floor_gib"] * 1024**3:
    errors.append("host availability missing or below six-GiB floor")
if min_admission is None or min_admission < design["host_floor_gib"] * 1024**3:
    errors.append("admission availability missing or below six-GiB floor")
if any(event_max.values()):
    errors.append(f"nonzero cgroup memory events: {event_max}")

result = {
    "passed": not errors,
    "complete_blocks": complete_blocks,
    "block_sources": block_sources,
    "paired_effects": dict(paired),
    "minimum_host_available_gib": min_host / 1024**3 if min_host is not None else None,
    "minimum_admission_available_gib": min_admission / 1024**3 if min_admission is not None else None,
    "maximum_cgroup_events": event_max,
    "clock_observations": {
        "gpu_hz_min_max": [min(gpu_clocks), max(gpu_clocks)] if gpu_clocks else None,
        "cpu_hz_min_max": [min(cpu_clocks), max(cpu_clocks)] if cpu_clocks else None,
        "emc_status_counts": dict(emc_statuses),
    },
    "block_local_dates": {str(k): sorted(v) for k, v in sorted(block_dates.items())},
    "tegrastats_tj_celsius_min_max": [min(tj_temperatures), max(tj_temperatures)] if tj_temperatures else None,
    "errors": errors,
}
(HERE / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["passed"] else 1)
