#!/usr/bin/env python3
"""Recompute paired output, speculative, and timing summaries for this campaign."""
import hashlib
import json
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign"


def load_check(block, arm, cell):
    report = json.loads((CAMPAIGN / f"block-{block}-{arm}" / "requests.json").read_text())
    checks = [x for x in report["checks"] if x["cell"] == cell]
    assert len(checks) == 1 and checks[0]["status"] == "pass", (block, arm, cell)
    return checks[0]


def stream_data(check):
    events = check["stream_observation"]["events"]
    text = "".join(e["event"].get("choices", [{}])[0].get("delta", {}).get("content", "")
                   for e in events if e.get("event", {}).get("choices"))
    final = next(e["event"] for e in reversed(events) if e.get("event", {}).get("usage"))
    return text, final["usage"], final["timings"]


def summary(name, get_value):
    deltas = [100 * (get_value(p["arms"]["candidate"]) / get_value(p["arms"]["baseline"]) - 1) for p in PAIRS]
    rng = random.Random(2026101116)
    boot = sorted(statistics.median(rng.choice(deltas) for _ in deltas) for _ in range(200_000))
    return {"median_paired_delta_percent": statistics.median(deltas),
            "pair_deltas_percent": deltas,
            "bootstrap_95_percentile_interval": [boot[4999], boot[194999]],
            "bootstrap_replicates": len(boot), "bootstrap_seed": 2026101116}


PAIRS = []
for block in range(7):
    pair = {"block": block, "arms": {}}
    for arm in ("baseline", "candidate"):
        warm = load_check(block, arm, "distinct-warmup-172")
        measured = load_check(block, arm, "heldout-2048-context16384")
        warm_text, warm_usage, warm_timing = stream_data(warm)
        text, usage, timing = stream_data(measured)
        assert warm_usage["prompt_tokens"] == 172 and warm_usage["completion_tokens"] == 64
        assert usage["prompt_tokens"] == 2048 and usage["completion_tokens"] == 128
        pair["arms"][arm] = {
            "warmup_sha256": hashlib.sha256(warm_text.encode()).hexdigest(),
            "output_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "client_elapsed_s": measured["client_elapsed_s"],
            "prompt_ms": timing["prompt_ms"], "predicted_ms": timing["predicted_ms"],
            "prompt_per_second": timing["prompt_per_second"],
            "predicted_per_second": timing["predicted_per_second"],
            "draft_n": timing["draft_n"], "draft_n_accepted": timing["draft_n_accepted"],
            "cache_slots": measured["metrics_after"]["conversation_cache"]["slots"],
        }
    b, c = pair["arms"]["baseline"], pair["arms"]["candidate"]
    assert b["warmup_sha256"] == c["warmup_sha256"]
    assert b["output_sha256"] == c["output_sha256"]
    assert b["draft_n"] == c["draft_n"] and b["draft_n_accepted"] == c["draft_n_accepted"]
    assert b["cache_slots"] == c["cache_slots"] == 4
    PAIRS.append(pair)

def state_signature(arm):
    lines = (ROOT / "state-check" / arm / "engine.log").read_text(errors="replace").splitlines()
    commits = [line for line in lines if "ACCEPTED_PREFIX position=" in line and
               (lambda m: m and int(m.group(1)) >= 2047)(re.search(r"position=(\d+)", line))]
    full = [line for line in lines if "STATE_HASH L=" in line and
            (lambda m: m and int(m.group(1)) >= 2048)(re.search(r"\bL=(\d+)", line))]
    gdn = [line for line in lines if "STATE_HASH_GDN " in line]
    return {"accepted_prefix_commits": commits, "full_state_records": full,
            "final_gdn_fingerprints": gdn[-4:]}


state_baseline = state_signature("baseline")
state_candidate = state_signature("candidate")
assert state_baseline == state_candidate
assert len(state_baseline["accepted_prefix_commits"]) == 3

out = {
    "pairs": PAIRS,
    "request": summary("request", lambda x: x["prompt_ms"] + x["predicted_ms"]),
    "client_elapsed": summary("client_elapsed", lambda x: x["client_elapsed_s"]),
    "prompt": summary("prompt", lambda x: x["prompt_ms"]),
    "decode": summary("decode", lambda x: x["predicted_ms"]),
    "parity": "all seven warmup and measured text hashes, token counts, speculative draft/accepted counts, and observed cache slots match within pairs",
    "traced_state_check": {"matched": True, **state_baseline},
}
(ROOT / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
for name in ("request", "client_elapsed", "prompt", "decode"):
    x = out[name]
    lo, hi = x["bootstrap_95_percentile_interval"]
    print(f"{name}: median={x['median_paired_delta_percent']:.3f}% 95%=[{lo:.3f}%, {hi:.3f}%] pairs=" +
          ",".join(f"{v:.3f}" for v in x["pair_deltas_percent"]))
print(out["parity"])
print("traced_state_check: matched 3 accepted-prefix commits, full state records, and final GDN fingerprints")
