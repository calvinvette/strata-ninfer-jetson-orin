#!/usr/bin/env python3
"""Summarize the E0 three-pair current-versus-pinned screening control."""
import hashlib
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "pinned-vs-current-corrected-screen3"
OUT = ROOT / "summary.json"
rng = random.Random(2026102503)


def load(block, arm):
    run = ROOT / f"block-{block}-{arm}"
    data = json.loads((run / "requests.json").read_text())
    measured = [r for r in data["checks"] if not r["warmup"]]
    if len(measured) != 1 or measured[0]["status"] != "pass":
        raise ValueError(f"invalid measured row: {block} {arm}")
    row = measured[0]
    t = row["response"]["timings"]
    engine = row["metrics_after"]["engine"]
    text = "".join(e.get("event", {}).get("choices", [{}])[0].get("delta", {}).get("content", "")
                   for e in row["stream_observation"]["events"])
    return {
        "prompt_tps": t["prompt_per_second"],
        "decode_tps": t["predicted_per_second"],
        "ttft_s": row["stream_observation"]["first_visible_delta_s"],
        "client_total_s": row["client_elapsed_s"],
        "drafts_offered": t["draft_n"],
        "drafts_accepted": t["draft_n_accepted"],
        "completion_tokens": row["response"]["usage"]["completion_tokens"],
        "expert_slots": engine["expert_slots"],
        "expert_cache_mib": engine["expert_cache_mib"],
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def median_bootstrap_ci(values, samples=20000):
    draws = [statistics.median(rng.choices(values, k=len(values))) for _ in range(samples)]
    draws.sort()
    return [draws[int(0.025 * samples)], draws[min(samples - 1, int(0.975 * samples))]]


campaign = json.loads((ROOT / "campaign.json").read_text())
if any(r["status"] != "pass" for r in campaign["runs"]):
    raise ValueError("campaign contains a non-passing arm")
records = []
for block in range(campaign["planned_blocks"]):
    baseline, candidate = load(block, "baseline"), load(block, "candidate")
    for arm in (baseline, candidate):
        if arm["drafts_offered"] != 0 or arm["drafts_accepted"] != 0:
            raise ValueError(f"MTP/draft counters are not zero in block {block}")
        if arm["expert_slots"] != 3903 or arm["expert_cache_mib"] != baseline["expert_cache_mib"]:
            raise ValueError(f"cache resource mismatch in block {block}")
        if arm["completion_tokens"] != 64:
            raise ValueError(f"wrong output length in block {block}")
    if baseline["text_sha256"] != candidate["text_sha256"]:
        raise ValueError(f"text mismatch in block {block}")
    records.append({"block": block, "baseline": baseline, "candidate": candidate})

metrics = {"prompt_tps": "higher is better", "decode_tps": "higher is better",
           "ttft_s": "lower is better", "client_total_s": "lower is better"}
summary = {}
for key, interpretation in metrics.items():
    b = [x["baseline"][key] for x in records]
    c = [x["candidate"][key] for x in records]
    ratios = [cv / bv for bv, cv in zip(b, c)]
    summary[key] = {
        "interpretation": interpretation,
        "baseline_median": statistics.median(b),
        "candidate_median": statistics.median(c),
        "paired_candidate_over_baseline_median": statistics.median(ratios),
        "paired_bootstrap_95_interval": median_bootstrap_ci(ratios),
        "pair_ratios": ratios,
    }

result = {
    "scope": "three-pair, same-day pinned Strata product-control screen; not an NInfer effect estimate",
    "uncertainty": "percentile bootstrap of the median paired ratio; three pairs are screening evidence only",
    "workload": "Coder IQ1_M, 8K context, 512 prompt + 64 output, FP16 KV, 128 prefill, 8 workers, static residency, MTP/drafts verified 0/0",
    "same_args_and_environment": True,
    "cache": {"actual_slots": 3903, "allocated_gib": 7.44,
              "resident_map_sha256_current_source": "d391d3b8fe1aa0361b6441aecff74279d0946fcb3529099af2eb4d69a4ca2859",
              "pinned_resident_map_hash": None},
    "api_text_identical_all_pairs": True,
    "metrics": summary,
    "blocks": records,
}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(OUT)
for key, row in summary.items():
    print(key, "baseline median", row["baseline_median"], "candidate median", row["candidate_median"],
          "paired ratio", row["paired_candidate_over_baseline_median"], "95%", row["paired_bootstrap_95_interval"])
