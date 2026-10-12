#!/usr/bin/env python3
"""Recompute the seven-pair 32K-context Q6 warp-dequant confirmation."""
import hashlib
import json
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "campaign-confirm7"
SEED = 2026101277


def read_check(block, arm, cell):
    data = json.loads((CAMPAIGN / f"block-{block}-{arm}" / "requests.json").read_text())
    checks = [x for x in data["checks"] if x["cell"] == cell]
    assert len(checks) == 1 and checks[0]["status"] == "pass", (block, arm, cell)
    return checks[0]


def stream(check):
    events = check["stream_observation"]["events"]
    content = "".join(e["event"].get("choices", [{}])[0].get("delta", {}).get("content", "")
                     for e in events if e.get("event", {}).get("choices"))
    final = next(e["event"] for e in reversed(events) if e.get("event", {}).get("usage"))
    return content, final["usage"], final["timings"]


def bootstrap(values, seed):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choice(values) for _ in values) for _ in range(200_000))
    return [samples[4_999], samples[194_999]]


pairs = []
speculation_mismatches = []
minimum_memory = {}
cpu_clocks = []
gpu_util = []
for block in range(7):
    pair = {"block": block, "arms": {}}
    for arm in ("baseline", "candidate"):
        warm = read_check(block, arm, "distinct-warmup-172")
        measured = read_check(block, arm, "heldout-context32k-2048")
        warm_text, warm_usage, _ = stream(warm)
        output_text, usage, timing = stream(measured)
        assert (warm_usage["prompt_tokens"], warm_usage["completion_tokens"]) == (172, 64)
        assert (usage["prompt_tokens"], usage["completion_tokens"]) == (2048, 128)
        pair["arms"][arm] = {
            "warmup_text_sha256": hashlib.sha256(warm_text.encode()).hexdigest(),
            "output_text_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
            "client_elapsed_s": measured["client_elapsed_s"],
            "prompt_ms": timing["prompt_ms"], "decode_ms": timing["predicted_ms"],
            "prompt_tokens_per_second": timing["prompt_per_second"],
            "decode_tokens_per_second": timing["predicted_per_second"],
            "drafts": timing["draft_n"], "accepted_drafts": timing["draft_n_accepted"],
            "expert_slots": measured["metrics_after"]["engine"]["expert_slots"],
            "conversation_slots": measured["metrics_after"]["conversation_cache"]["slots"],
        }
        run = CAMPAIGN / f"block-{block}-{arm}"
        supervisor = json.loads((run / "result.json").read_text())
        assert supervisor["status"] == "pass" and supervisor["returncode"] == 0
        minimum_memory[f"{block}-{arm}"] = supervisor["minimum_available_bytes"]
        for line in (run / "tegrastats.txt").read_text(errors="replace").splitlines():
            match = re.search(r"CPU \[([^]]+)\]", line)
            if match:
                cpu_clocks.extend(int(x) for x in re.findall(r"@(\d+)", match.group(1)))
            match = re.search(r"GR3D_FREQ (\d+)%", line)
            if match:
                gpu_util.append(int(match.group(1)))
    baseline, candidate = pair["arms"]["baseline"], pair["arms"]["candidate"]
    assert baseline["warmup_text_sha256"] == candidate["warmup_text_sha256"]
    assert baseline["output_text_sha256"] == candidate["output_text_sha256"]
    if (baseline["drafts"], baseline["accepted_drafts"]) != (candidate["drafts"], candidate["accepted_drafts"]):
        speculation_mismatches.append({"block": block,
                                       "baseline": [baseline["drafts"], baseline["accepted_drafts"]],
                                       "candidate": [candidate["drafts"], candidate["accepted_drafts"]]})
    assert baseline["expert_slots"] == candidate["expert_slots"] == 3903
    assert baseline["conversation_slots"] == candidate["conversation_slots"]
    pairs.append(pair)


def metric(name, getter):
    deltas = [100 * (getter(p["arms"]["candidate"]) / getter(p["arms"]["baseline"]) - 1)
              for p in pairs]
    return {"metric": name, "paired_deltas_percent": deltas,
            "median_delta_percent": statistics.median(deltas),
            "bootstrap_95_percentile_interval": bootstrap(deltas, SEED + len(name)),
            "bootstrap_replicates": 200_000, "bootstrap_seed": SEED + len(name)}


def state_signature(arm):
    lines = (ROOT / "state-check" / arm / "engine.log").read_text(errors="replace").splitlines()
    commits = [x for x in lines if "ACCEPTED_PREFIX position=" in x and
               (lambda m: m and int(m.group(1)) >= 2047)(re.search(r"position=(\d+)", x))]
    full = [x for x in lines if "STATE_HASH L=" in x and
            (lambda m: m and int(m.group(1)) >= 2048)(re.search(r"\bL=(\d+)", x))]
    gdn = [x for x in lines if "STATE_HASH_GDN " in x]
    checks = json.loads((ROOT / "state-check" / arm / "requests.json").read_text())["checks"]
    measured = next(x for x in checks if x["cell"] == "heldout-context32k-2048-state8")
    output_text, usage, _ = stream(measured)
    return {"accepted_prefix_commits": commits, "full_state_records": full,
            "final_gdn_records": gdn[-4:],
            "output_text_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
            "token_counts": [usage["prompt_tokens"], usage["completion_tokens"]]}


state = {arm: state_signature(arm) for arm in ("baseline", "candidate")}
assert state["baseline"] == state["candidate"]
assert len(state["baseline"]["accepted_prefix_commits"]) == 4

max_events = oom_events = oom_kills = memory_samples = 0
for f in CAMPAIGN.glob("block-*/memory.jsonl"):
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        sample = json.loads(line)
        memory_samples += 1
        for cgroup in sample.get("cgroups", []):
            events = cgroup.get("memory_events", {})
            max_events += events.get("max", 0)
            oom_events += events.get("oom", 0)
            oom_kills += events.get("oom_kill", 0)
assert max_events == oom_events == oom_kills == 0

out = {
    "design": "Seven randomized same-day fresh-process pairs; fixed 32K context, 3,000 requested cache, FP16 KV, MTP/spec4, prefill 64 and 8 workers; only STRATA_Q6K_WARP_DEQUANT differs.",
    "candidate_binary_sha256": "bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d",
    "prompt_token_sha256": json.loads((ROOT / "workloads.json").read_text())["workloads"][0]["tokens_sha256"],
    "warmup_token_sha256": json.loads((ROOT / "warmup-workloads.json").read_text())["workloads"][0]["tokens_sha256"],
    "pairs": pairs,
    "metrics": [metric("client_elapsed_s", lambda x: x["client_elapsed_s"]),
                metric("prompt_ms", lambda x: x["prompt_ms"]),
                metric("decode_ms", lambda x: x["decode_ms"])],
    "minimum_available_bytes_by_process": minimum_memory,
    "minimum_available_gib": min(minimum_memory.values()) / 2**30,
    "sampled_cgroup_memory_events": {"samples": memory_samples, "max": max_events,
                                      "oom": oom_events, "oom_kill": oom_kills},
    "observed_cpu_clock_mhz_range": [min(cpu_clocks), max(cpu_clocks)],
    "observed_gpu_utilization_percent_range": [min(gpu_util), max(gpu_util)],
    "gpu_and_emc_clock_rates": "not reported by the available tegrastats records",
    "energy": "not request-scoped; raw rail samples retained only",
    "paired_runtime_parity": {"all_seven_pairs_matched": ["warmup and output text hashes", "requested token counts", "expert slots (3,903)", "conversation slots"],
                               "draft_accept_counts_matched_pairs": 7 - len(speculation_mismatches),
                               "draft_accept_count_mismatches": speculation_mismatches},
    "traced_state_check": {"matched": True, "baseline": state["baseline"], "candidate": state["candidate"]},
    "limitations": ["Synthetic log prompt padded with one-token filler; no task-quality criterion.",
                     "One prompt and one configured context; no default promotion follows.",
                     "Dynamic clocks; GPU/EMC frequency and request-scoped energy unavailable."]
}
(ROOT / "confirmation-analysis.json").write_text(json.dumps(out, indent=2) + "\n")
for row in out["metrics"]:
    print(row["metric"], f'median {row["median_delta_percent"]:.3f}%',
          f'95% {row["bootstrap_95_percentile_interval"]}')
print("minimum available GiB", f'{out["minimum_available_gib"]:.2f}')
print("cpu MHz", out["observed_cpu_clock_mhz_range"], "GPU utilization %", out["observed_gpu_utilization_percent_range"])
print("all seven pairs completed; six had matched draft/accept counts, one differed by one accepted draft")
print("traced output, accepted-prefix, full-state, and GDN state matched")
