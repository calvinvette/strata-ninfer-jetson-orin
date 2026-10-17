#!/usr/bin/env python3
"""Independent correctness and paired-effect review for the Coder quant screen."""
import argparse
import json
import random
import statistics
from pathlib import Path

GIB = 1024 ** 3


def percentile(values, q):
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def bootstrap_median_interval(values, seed, draws=20000):
    rng = random.Random(seed)
    samples = [statistics.median(rng.choices(values, k=len(values))) for _ in range(draws)]
    return [percentile(samples, .025), percentile(samples, .975)]


def response_for(root, run):
    data = json.loads((root / f"block-{run['block']}-{run['variant']}" / "requests.json").read_text())
    measured = [row for row in data["checks"] if not row.get("warmup") and row.get("cell") != "warmup-512"]
    if len(measured) != 1:
        raise AssertionError(f"expected one measured row, got {len(measured)}")
    row = measured[0]
    if row.get("status") != "pass":
        raise AssertionError(f"request failed: {row.get('reason')}")
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-prompt", type=int, required=True)
    parser.add_argument("--expected-codes", nargs=3, required=True)
    parser.add_argument("--require-cache-match", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    campaign = json.loads((root / "campaign.json").read_text())
    rows = campaign["runs"]
    blocks = sorted({run["block"] for run in rows})
    if len(blocks) < 3 or any(run.get("status") != "pass" for run in rows):
        raise AssertionError("campaign is incomplete or has a failed arm")
    if any(set(run["variant"] for run in rows if run["block"] == block) != {"baseline", "candidate"}
           for block in blocks):
        raise AssertionError("each paired block must contain one baseline and one candidate arm")
    confirmation = len(blocks) >= 7 and "heldout" in str(campaign.get("workloads", "")).lower()
    by_block = {block: {} for block in blocks}
    checked = []
    for run in rows:
        row = response_for(root, run)
        response = row["response"]
        content = response["choices"][0]["message"]["content"]
        codes = args.expected_codes
        positions = [content.find(code) for code in codes]
        if not (all(content.count(code) == 1 for code in codes) and
                all(pos >= 0 for pos in positions) and positions == sorted(positions)):
            raise AssertionError(f"marker oracle failed in block {run['block']} {run['variant']}: {content!r}")
        usage = response.get("usage", {})
        timings = response.get("timings", {})
        if usage.get("prompt_tokens") != args.expected_prompt or usage.get("completion_tokens", 0) <= 0:
            raise AssertionError("token counts do not match the campaign workload")
        if timings.get("cache_n") != 0:
            raise AssertionError("measured prompt unexpectedly reused cache")
        engine = row.get("metrics_after", {}).get("engine", {})
        if engine.get("max_context") != 8192 or engine.get("kv") != "fp16" or engine.get("pool_workers") != 8:
            raise AssertionError("runtime profile did not match the shared 8K/FP16/eight-worker settings")
        run_dir = root / f"block-{run['block']}-{run['variant']}"
        supervisor = json.loads((run_dir / "result.json").read_text())
        if supervisor.get("status") != "pass":
            raise AssertionError("supervisor did not pass")
        if supervisor.get("minimum_available_bytes", 0) < 6 * GIB or supervisor.get("minimum_admission_available_bytes", 0) < 6 * GIB:
            raise AssertionError("six-GiB physical/admission floor was breached")
        mem = [json.loads(line) for line in (run_dir / "memory.jsonl").read_text().splitlines()]
        scoped = [cg for sample in mem for cg in sample.get("cgroups", [])
                  if cg.get("max_bytes") == 28 * GIB and "run-" in cg.get("path", "")]
        if not scoped:
            raise AssertionError("per-arm 28-GiB memory scope was not observed")
        events = {name: max(cg.get("memory_events", {}).get(name, 0) for cg in scoped)
                  for name in ("low", "high", "max", "oom", "oom_kill")}
        if any(events.values()):
            raise AssertionError(f"nonzero cgroup memory events: {events}")
        by_block[run["block"]][run["variant"]] = {
            "prompt_seconds": timings["prompt_ms"] / 1000,
            "decode_tokens_per_second": timings["predicted_per_second"],
            "client_total_seconds": row["client_elapsed_s"],
            "first_visible_delta_seconds": row.get("stream_observation", {}).get("first_visible_delta_s"),
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "answer": content,
            "minimum_host_gib": supervisor["minimum_available_bytes"] / GIB,
            "minimum_admission_gib": supervisor["minimum_admission_available_bytes"] / GIB,
            "scope_peak_gib": max(cg["current_bytes"] for cg in scoped) / GIB,
            "actual_expert_slots": engine.get("expert_slots"),
            "actual_expert_cache_mib": engine.get("expert_cache_mib"),
            "memory_events": events,
        }
        checked.append({"block": run["block"], "variant": run["variant"],
                        "marker_oracle": "pass", "request_status": row["status"],
                        "memory_guard": "pass"})
    metrics = ("prompt_seconds", "decode_tokens_per_second", "client_total_seconds",
               "first_visible_delta_seconds")
    effects = {}
    cache_match = {}
    for metric in metrics:
        paired = []
        for block in blocks:
            pair = by_block[block]
            q2, iq = pair["baseline"][metric], pair["candidate"][metric]
            paired.append((iq / q2 - 1) * 100)
        effects[metric] = {
            "iq1_m_vs_q2_0_paired_percent_changes": paired,
            "median_paired_percent_change": statistics.median(paired),
            "paired_block_bootstrap_95_interval_percent": bootstrap_median_interval(paired, 20261017 + len(metric)),
            "interval_method": "20,000 resamples of paired-block deltas; median and percentile interval",
            "interpretation": "held-out confirmation" if confirmation else "screen only",
        }
    for block in blocks:
        pair = by_block[block]
        q2_mib = pair["baseline"]["actual_expert_cache_mib"]
        iq1_mib = pair["candidate"]["actual_expert_cache_mib"]
        cache_match[str(block)] = {"q2_0_mib": q2_mib, "iq1_m_mib": iq1_mib,
                                   "difference_mib": iq1_mib - q2_mib,
                                   "within_2_mib": abs(iq1_mib - q2_mib) <= 2}
    if args.require_cache_match and not all(v["within_2_mib"] for v in cache_match.values()):
        raise AssertionError(f"effective expert-cache footprints were not matched: {cache_match}")
    output = {
        "status": "pass",
        "independent_review": True,
        "scope": campaign.get("design", "paired screening"),
        "confirmation": confirmation,
        "quantization_mapping": {"baseline": "Q2_0", "candidate": "IQ1_M"},
        "expected_prompt_tokens": args.expected_prompt,
        "expected_codes": args.expected_codes,
        "runtime_checks": checked,
        "effective_cache_match_by_block": cache_match,
        "paired_metrics": effects,
        "per_block": by_block,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
