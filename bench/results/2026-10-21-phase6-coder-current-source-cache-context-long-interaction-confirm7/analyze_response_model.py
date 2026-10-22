#!/usr/bin/env python3
"""Fit block-adjusted log-response models for the 2x2 cache/context campaign."""
from collections import defaultdict
import json
import math
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools/integration"))
from summarize_controls import metrics

analysis = json.loads((HERE / "analysis.json").read_text())
if not analysis.get("passed") or analysis.get("complete_blocks") != list(range(1, 8)):
    raise SystemExit("the seven-block campaign analyzer must pass before model fitting")

cells = defaultdict(dict)
for block in range(1, 8):
    block_dir = HERE / f"per-cell-scopes/block-{block:02d}"
    if block == 7 and (HERE / "per-cell-scopes/block-07-replacement").exists():
        block_dir = HERE / "per-cell-scopes/block-07-replacement"
    manifest = json.loads((block_dir / "campaign.json").read_text())
    for cache in (1500, 3000):
        for context in (8192, 16384):
            name = f"cache{cache}-ctx{context}"
            req = json.loads((block_dir / name / "requests.json").read_text())
            measured = [x for x in req["checks"] if not x.get("warmup")]
            if len(measured) != 1 or measured[0].get("status") != "pass":
                raise SystemExit(f"block {block} {name}: invalid measured response")
            cells[block][(cache, context)] = metrics(measured[0])

METRICS = ("client_total_s", "client_ttft_s", "prompt_tps", "decode_tps")
N_BOOT = 10000
seed = 2026102229
rng = random.Random(seed)

def block_contrasts(rows):
    y = {(cache, context): value for _, cache, context, value in rows}
    if set(y) != {(c, x) for c in (1500, 3000) for x in (8192, 16384)}:
        raise ValueError("each block must contain the complete randomized 2x2")
    cache = ((y[(3000, 8192)] + y[(3000, 16384)]) -
             (y[(1500, 8192)] + y[(1500, 16384)])) / 2.0
    context = ((y[(1500, 16384)] + y[(3000, 16384)]) -
               (y[(1500, 8192)] + y[(3000, 8192)])) / 2.0
    interaction = (y[(3000, 16384)] - y[(3000, 8192)] -
                   y[(1500, 16384)] + y[(1500, 8192)])
    return cache, context, interaction, statistics.mean(y.values()), y

result = {
    "model": "log(response) ~ cache[-0.5,+0.5] * context[-0.5,+0.5] + paired-block fixed effects",
    "observations": 28,
    "block_count": 7,
    "parameter_count": 10,
    "bootstrap": {"unit": "whole randomized four-cell block", "replicates": N_BOOT, "seed": seed},
    "outcomes": {},
    "interpretation": "exploratory model diagnostics; paired-block median bootstrap in analysis.json remains primary",
}

for metric_name in METRICS:
    by_block = {}
    for block in range(1, 8):
        rows = []
        for cache in (1500, 3000):
            for context in (8192, 16384):
                value = float(cells[block][(cache, context)][metric_name])
                if value <= 0 or not math.isfinite(value):
                    raise SystemExit(f"{metric_name}: nonpositive/nonfinite response")
                row = (block, cache, context, math.log(value))
                rows.append(row)
        by_block[block] = rows
    contrasts = {block: block_contrasts(rows) for block, rows in by_block.items()}
    effects = [statistics.mean(contrasts[b][i] for b in range(1, 8)) for i in range(3)]
    block_means = {b: contrasts[b][3] for b in range(1, 8)}
    grand_mean = statistics.mean(block_means.values())
    predictions = {}
    residual_rows = []
    for block in range(1, 8):
        _, _, _, block_mean, values = contrasts[block]
        for (cache, context), observed in values.items():
            c = -0.5 if cache == 1500 else 0.5
            x = -0.5 if context == 8192 else 0.5
            predicted = block_mean + effects[0] * c + effects[1] * x + effects[2] * c * x
            residual_rows.append((block, cache, context, observed - predicted, observed))
    sse = sum(row[3] ** 2 for row in residual_rows)
    sst = sum((row[4] - grand_mean) ** 2 for row in residual_rows)
    rank = 10  # 7 block intercepts + cache, context and cache:context; all 2x2 cells are present
    dof = 28 - rank
    sigma = math.sqrt(sse / dof)
    # In this balanced blocked design each row's leverage is 1/4 + 3/(4*7).
    leverage = 0.25 + 3.0 / 28.0
    studentized = [r[3] / (sigma * math.sqrt(1.0 - leverage)) if sigma else 0.0 for r in residual_rows]
    boot = [[], [], []]
    for _ in range(N_BOOT):
        picked = rng.choices(range(1, 8), k=7)
        for i in range(3):
            boot[i].append(statistics.mean(contrasts[b][i] for b in picked))
    terms = {}
    for i, name in enumerate(("cache", "context", "cache_by_context")):
        sorted_boot = sorted(boot[i])
        lo, hi = sorted_boot[int(0.025 * N_BOOT)], sorted_boot[int(0.975 * N_BOOT)]
        terms[name] = {
            "log_coefficient": effects[i],
            "ratio_percent": (math.exp(effects[i]) - 1.0) * 100.0,
            "paired_block_cluster_bootstrap_95_percent_interval": [
                (math.exp(lo) - 1.0) * 100.0,
                (math.exp(hi) - 1.0) * 100.0,
            ],
        }
    worst = sorted(range(len(studentized)), key=lambda i: abs(studentized[i]), reverse=True)[:3]
    max_studentized = max(abs(x) for x in studentized)
    result["outcomes"][metric_name] = {
        "rank": rank,
        "full_rank": rank == 10,
        "residual_degrees_of_freedom": dof,
        "r_squared": 1.0 - sse / sst if sst else 1.0,
        "max_absolute_internally_studentized_residual": max_studentized,
        "residual_screen_abs_studentized_lt_3": max_studentized < 3.0,
        "largest_residual_cells": [
            {"block": residual_rows[i][0], "cache_mib": residual_rows[i][1], "context_tokens": residual_rows[i][2],
             "studentized_residual": studentized[i], "log_residual": residual_rows[i][3]}
            for i in worst
        ],
        "terms": terms,
        "model_warning": ("largest residual is below the exploratory 3.0 screen; retain paired-block inference as primary"
                          if max_studentized < 3.0 else
                          "largest residual exceeds the exploratory 3.0 screen; model is diagnostic only, retain paired-block inference as primary"),
    }

out = HERE / "response-model.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
