#!/usr/bin/env python3
"""Recompute paired timing and state-parity summaries for this campaign."""
import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAIRS = []


def load_arm(block, arm):
    folder = "campaign" if block < 3 else "extension4"
    return json.loads((ROOT / folder / f"block-{block}-{arm}/requests.json").read_text())


for block in range(7):
    b, c = (load_arm(block, arm) for arm in ("baseline", "candidate"))
    bcheck = next(x for x in b["checks"] if x["round"] == 0)
    ccheck = next(x for x in c["checks"] if x["round"] == 0)
    br, cr = bcheck["response"], ccheck["response"]
    assert br["usage"]["prompt_tokens"] == cr["usage"]["prompt_tokens"] == 512
    assert br["usage"]["completion_tokens"] == cr["usage"]["completion_tokens"] == 64
    assert br["choices"][0]["message"]["content"] == cr["choices"][0]["message"]["content"]
    assert br["timings"]["draft_n"] == cr["timings"]["draft_n"]
    assert br["timings"]["draft_n_accepted"] == cr["timings"]["draft_n_accepted"]
    PAIRS.append({
        "block": block,
        "baseline": {k: br["timings"][k] for k in ("prompt_ms", "predicted_ms")},
        "candidate": {k: cr["timings"][k] for k in ("prompt_ms", "predicted_ms")},
        "baseline_request_ms": bcheck["client_elapsed_s"] * 1000,
        "candidate_request_ms": ccheck["client_elapsed_s"] * 1000,
        "output_sha256": hashlib.sha256(br["choices"][0]["message"]["content"].encode()).hexdigest(),
        "draft_n": br["timings"]["draft_n"],
        "draft_n_accepted": br["timings"]["draft_n_accepted"],
    })


def pct_delta(x, y):
    return 100 * (y / x - 1)


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def summarize(name, fn):
    deltas = [pct_delta(fn(p["baseline"]), fn(p["candidate"])) for p in PAIRS]
    rng = random.Random(2026101182)
    boot = [median([rng.choice(deltas) for _ in deltas]) for _ in range(200000)]
    boot.sort()
    return {"median_paired_delta_percent": median(deltas), "pair_deltas_percent": deltas,
            "bootstrap_95_percentile_interval": [boot[4999], boot[194999]],
            "bootstrap_replicates": len(boot), "bootstrap_seed": 2026101182}


def state_signatures(arm):
    lines = (ROOT / f"state-check/{arm}/engine.log").read_text(errors="replace").splitlines()
    # Keep the measured request only: its commit positions start at 511/512.
    commits = [x for x in lines if "ACCEPTED_PREFIX position=" in x and
               (lambda m: m and int(m.group(1)) >= 511)(re.search(r"position=(\d+)", x))]
    full = [x for x in lines if "STATE_HASH L=" in x and
            (lambda m: m and int(m.group(1)) >= 512)(re.search(r"STATE_HASH L=(\d+)", x))]
    gdn = [x for x in lines if "STATE_HASH_GDN " in x]
    return {"accepted_prefix_lines": commits, "final_state_lines": full[-1:],
            "gdn_hash_lines": gdn[-4:]}


state_b, state_c = state_signatures("baseline"), state_signatures("candidate")
state_match = state_b == state_c
assert state_match, "measured accepted-prefix/state hashes differ"

out = {
    "pairs": PAIRS,
    "request": summarize("request", lambda x: x["prompt_ms"] + x["predicted_ms"]),
    "prompt": summarize("prompt", lambda x: x["prompt_ms"]),
    "decode": summarize("decode", lambda x: x["predicted_ms"]),
    "state_check": {"matched": state_match, "baseline": state_b, "candidate": state_c},
}
(ROOT / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
for name in ("request", "prompt", "decode"):
    x = out[name]
    print(name, f"median={x['median_paired_delta_percent']:.3f}%",
          f"95%=[{x['bootstrap_95_percentile_interval'][0]:.3f}%, {x['bootstrap_95_percentile_interval'][1]:.3f}%]",
          "pairs=" + ",".join(f"{v:.3f}" for v in x["pair_deltas_percent"]))
print("state_match", state_match, "accepted-prefix boundaries", len(state_b["accepted_prefix_lines"]))
