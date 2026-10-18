#!/usr/bin/env python3
"""Compare prefill-chunk effects across independent short and near-limit Q2_0 blocks."""
import argparse
import json
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
LONG = HERE.parent / "2026-10-18-phase6-q2-cache-prefill-heldout-confirm7"
BLOCKS = tuple(f"block-{i:02d}" for i in range(1, 8))
CACHES = (3000, 3500)
CHUNKS = (32, 128)
EXPECTED_SHORT = "EARLY=TUNDRA-ORBIT-593, MIDDLE=COBALT-MAPLE-248, LATE=GRANITE-COMET-761, SUM=1602"


def load_campaign(root, expected_answer=None):
    workload = json.loads((root / "workload.json").read_text())["workloads"][0]
    results = {"prompt_ms": {}, "request_ms": {}}
    for block in BLOCKS:
        manifest = json.loads((root / block / "campaign.json").read_text())
        assert manifest["independent_block_confirmation"] and manifest["rounds_per_service"] == 1
        assert len(manifest["cells"]) == 4
        for cell in manifest["cells"]:
            assert cell["status"] == "pass", (root, block, cell["name"], cell["status"])
            cache = cell["expert_cache_argument"]
            chunk = cell["prefill_chunk_tokens"]
            assert cache in CACHES and chunk in CHUNKS
            folder = root / block / cell["name"]
            request = json.loads((folder / "requests.json").read_text())
            measured = [row for row in request["checks"] if not row["warmup"]]
            assert len(measured) == 1 and measured[0]["status"] == "pass"
            response = measured[0]["response"]
            timing = response["timings"]
            usage = response["usage"]
            assert usage["prompt_tokens"] == workload["prompt_tokens"]
            assert timing["prompt_n"] == workload["prompt_tokens"] and timing.get("cache_n", 0) == 0
            if expected_answer is not None:
                answer = response["choices"][0]["message"]["content"]
                assert answer == expected_answer, (block, cache, chunk, answer)
            key = (cache, chunk)
            results["prompt_ms"].setdefault(key, {})[block] = timing["prompt_ms"]
            results["request_ms"].setdefault(key, {})[block] = timing["prompt_ms"] + timing["predicted_ms"]
    for metric in results.values():
        assert len(metric) == 4 and all(len(row) == 7 for row in metric.values())
    return {"prompt_tokens": workload["prompt_tokens"], **results}


def block_effects(data, metric, cache):
    cells = data[metric]
    return [100.0 * (cells[(cache, 128)][block] / cells[(cache, 32)][block] - 1.0)
            for block in BLOCKS]


def median_ci(values, seed, draws=50000):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(draws))
    return [samples[int(0.025 * draws)], samples[int(0.975 * draws)]]


def independent_interaction_ci(short, long, seed, draws=50000):
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        short_median = statistics.median(rng.choices(short, k=len(short)))
        long_median = statistics.median(rng.choices(long, k=len(long)))
        samples.append(long_median - short_median)
    samples.sort()
    return [samples[int(0.025 * draws)], samples[int(0.975 * draws)]]


def summarize(data):
    rows = []
    for metric in ("prompt_ms", "request_ms"):
        for cache in CACHES:
            effects = block_effects(data, metric, cache)
            rows.append({"metric": metric, "cache_slots": cache,
                         "contrast": "chunk 128 vs 32",
                         "block_effects_percent": effects,
                         "median_effect_percent": statistics.median(effects),
                         "paired_block_bootstrap_95pct_percent": median_ci(effects, 20261018 + cache)})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=HERE / "workload-interaction-analysis.json")
    a = ap.parse_args()
    short = load_campaign(HERE, EXPECTED_SHORT)
    long = load_campaign(LONG)
    short_effects = summarize(short)
    long_effects = summarize(long)
    interactions = []
    for metric in ("prompt_ms", "request_ms"):
        for cache in CACHES:
            se = block_effects(short, metric, cache)
            le = block_effects(long, metric, cache)
            # Positive means the chunk-128 improvement is larger on the near-limit task.
            estimate = statistics.median(le) - statistics.median(se)
            interactions.append({
                "metric": metric,
                "cache_slots": cache,
                "contrast": "near-limit chunk effect minus short-task chunk effect",
                "short_block_effects_percent": se,
                "near_limit_block_effects_percent": le,
                "median_interaction_percentage_points": estimate,
                "independent_block_bootstrap_95pct_percentage_points": independent_interaction_ci(
                    se, le, 2026101800 + cache + (0 if metric == "prompt_ms" else 100)),
                "resampling_unit": "independent process/block within each seven-block campaign",
            })
    out = {
        "scope": "Q2_0 FP16 KV, MTP off, 8K context, eight workers, prompt cache/adaptive swaps disabled; exact 3,000/3,500 expert slots and chunks 32/128.",
        "short_workload": {"prompt_tokens": short["prompt_tokens"], "answer": EXPECTED_SHORT,
                           "independent_oracle": "593 + 248 + 761 = 1602", "blocks": 7, "cells": 28},
        "near_limit_workload": {"prompt_tokens": long["prompt_tokens"], "answer": json.loads((LONG / "workload.json").read_text())["workloads"][0]["expected_codes"], "blocks": 7, "cells": 28},
        "short_task_chunk_effects": short_effects,
        "near_limit_chunk_effects": long_effects,
        "workload_interactions": interactions,
        "interpretation": "The interaction contrasts do not imply equal prompt content or output lengths; they test whether the chunk effect changes between these two qualified retrieval tasks. No setting is promoted by this analysis.",
    }
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"workload_interactions": interactions}, indent=2))


if __name__ == "__main__":
    main()
