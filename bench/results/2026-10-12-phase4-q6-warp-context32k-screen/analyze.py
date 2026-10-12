#!/usr/bin/env python3
"""Analyze the three-pair context-32K Q6 warp-dequant screening campaign."""
import hashlib
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign-valid"
SEED = 2026101232


def get_check(block, arm, cell):
    p = CAMPAIGN / f"block-{block}-{arm}" / "requests.json"
    report = json.loads(p.read_text())
    found = [x for x in report["checks"] if x["cell"] == cell]
    assert len(found) == 1 and found[0]["status"] == "pass", (block, arm, cell)
    return found[0]


def stream(check):
    events = check["stream_observation"]["events"]
    content = "".join(e["event"].get("choices", [{}])[0].get("delta", {}).get("content", "")
                     for e in events if e.get("event", {}).get("choices"))
    final = next(e["event"] for e in reversed(events) if e.get("event", {}).get("usage"))
    return content, final["usage"], final["timings"]


def ci(values, seed):
    rng = random.Random(seed)
    reps = sorted(statistics.median(rng.choice(values) for _ in values) for _ in range(100_000))
    return [reps[2499], reps[97499]]


pairs = []
for block in range(3):
    pair = {"block": block, "arms": {}}
    for arm in ("baseline", "candidate"):
        warm = get_check(block, arm, "distinct-warmup-172")
        measured = get_check(block, arm, "heldout-context32k-2048")
        warm_text, warm_usage, _ = stream(warm)
        text, usage, timing = stream(measured)
        assert (warm_usage["prompt_tokens"], warm_usage["completion_tokens"]) == (172, 64)
        assert (usage["prompt_tokens"], usage["completion_tokens"]) == (2048, 128)
        pair["arms"][arm] = {
            "warmup_text_sha256": hashlib.sha256(warm_text.encode()).hexdigest(),
            "output_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "client_elapsed_s": measured["client_elapsed_s"],
            "prompt_ms": timing["prompt_ms"], "decode_ms": timing["predicted_ms"],
            "prompt_tokens_per_second": timing["prompt_per_second"],
            "decode_tokens_per_second": timing["predicted_per_second"],
            "drafts": timing["draft_n"], "accepted_drafts": timing["draft_n_accepted"],
            "expert_slots": measured["metrics_after"]["engine"]["expert_slots"],
            "conversation_slots": measured["metrics_after"]["conversation_cache"]["slots"],
        }
    b, c = pair["arms"]["baseline"], pair["arms"]["candidate"]
    assert b["warmup_text_sha256"] == c["warmup_text_sha256"]
    assert b["output_text_sha256"] == c["output_text_sha256"]
    assert (b["drafts"], b["accepted_drafts"]) == (c["drafts"], c["accepted_drafts"])
    assert b["expert_slots"] == c["expert_slots"] == 3903
    assert b["conversation_slots"] == c["conversation_slots"]
    pairs.append(pair)


def metric(label, f):
    deltas = [100 * (f(p["arms"]["candidate"]) / f(p["arms"]["baseline"]) - 1) for p in pairs]
    return {"label": label, "paired_deltas_percent": deltas,
            "median_delta_percent": statistics.median(deltas),
            "bootstrap_95_interval_percent": ci(deltas, SEED + len(label)),
            "replicates": 100_000, "seed": SEED + len(label)}


memory = {}
for block in range(3):
    for arm in ("baseline", "candidate"):
        r = json.loads((CAMPAIGN / f"block-{block}-{arm}" / "result.json").read_text())
        assert r["status"] == "pass" and r["returncode"] == 0
        memory[f"{block}-{arm}"] = r["minimum_available_bytes"]

output = {
    "design": "Three randomized same-day process pairs; fixed 32K configured context, 3,000 requested expert slots, FP16 KV, spec4, 64-token prefill, 8 workers; only STRATA_Q6K_WARP_DEQUANT differs.",
    "candidate_binary_sha256": "bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d",
    "prompt_tokens_sha256": json.loads((ROOT / "workloads.json").read_text())["workloads"][0]["tokens_sha256"],
    "warmup_tokens_sha256": json.loads((ROOT / "warmup-workloads.json").read_text())["workloads"][0]["tokens_sha256"],
    "pairs": pairs,
    "metrics": [metric("client_elapsed_s", lambda x: x["client_elapsed_s"]),
                metric("prompt_ms", lambda x: x["prompt_ms"]),
                metric("decode_ms", lambda x: x["decode_ms"])],
    "minimum_available_bytes_by_process": memory,
    "minimum_available_gib": min(memory.values()) / 2**30,
    "limitations": ["Three-pair screening evidence only; seven-pair independent confirmation and a traced accepted-prefix state check are needed before broader qualification.",
                     "Synthetic incident log padded to exact length; no task-quality criterion was measured.",
                     "Dynamic clocks and no request-scoped energy measurement."]
}
(ROOT / "analysis.json").write_text(json.dumps(output, indent=2) + "\n")
for m in output["metrics"]:
    print(m["label"], f'median {m["median_delta_percent"]:.3f}%',
          f'95% {m["bootstrap_95_interval_percent"]}')
print("minimum available GiB", f'{output["minimum_available_gib"]:.2f}')
print("all paired warmup/output text, token counts, speculation counts, and cache capacities matched")
