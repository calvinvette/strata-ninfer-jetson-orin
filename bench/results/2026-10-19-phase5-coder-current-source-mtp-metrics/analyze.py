#!/usr/bin/env python3
"""Join current-source MTP round/state traces with decode-stage timing."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "bench/results/2026-10-19-phase5-coder-current-source-mtp-metrics"
TIMING = re.compile(
    r"strata decode timing: (?P<windows>\d+) windows, avg T (?P<avg_t>[\d.]+), "
    r"(?P<tokens_window>[\d.]+) tokens/window, (?P<total>[\d.]+) ms/window = verify "
    r"(?P<verify>[\d.]+) \(GPU-reach wait (?P<wait>[\d.]+) \+ per-layer host (?P<host>[\d.]+) "
    r"\[plan (?P<plan>[\d.]+) actq (?P<actq>[\d.]+) jobs (?P<jobs>[\d.]+) CPU (?P<cpu>[\d.]+)\] "
    r"\+ stage (?P<stage>[\d.]+)\) \+ commit/emit (?P<commit>[\d.]+) \+ draft "
    r"(?P<draft>[\d.]+);"
)
data = json.loads((CAMPAIGN / "run-2048/results.json").read_text())
supervisor = json.loads((CAMPAIGN / "supervisor-2048/result.json").read_text())
samples = [json.loads(line) for line in (CAMPAIGN / "supervisor-2048/memory.jsonl").read_text().splitlines()]
scoped = [cg for sample in samples for cg in sample.get("cgroups", [])
          if cg.get("max_bytes") == 28 * 1024**3]
events = {key: max((cg.get("memory_events", {}).get(key, 0) for cg in scoped), default=0)
          for key in ("low", "high", "max", "oom", "oom_kill")}
if not data.get("passed") or supervisor.get("status") != "pass":
    raise SystemExit("accepted-prefix comparison or supervisor did not pass")
if supervisor["minimum_available_bytes"] < 6 * 1024**3 or supervisor["minimum_admission_available_bytes"] < 6 * 1024**3:
    raise SystemExit("six-GiB physical/admission availability floor breached")
if any(events.values()):
    raise SystemExit(f"cgroup memory events observed: {events}")

rows = []
for arm in data["arms"]:
    spec = arm["spec"]
    name = arm["name"]
    record = arm["records"][0]
    trace = record["accepted_prefix_trace"]
    log = (CAMPAIGN / f"run-2048/{name}.log").read_text(errors="replace")
    matches = TIMING.findall(log)
    if len(matches) != 1:
        raise SystemExit(f"{name}: expected one decode timing record, got {len(matches)}")
    fields = {key: float(value) for key, value in zip(TIMING.groupindex, matches[0])}
    windows = len(trace)
    emitted = sum(item["committed"] for item in trace)
    accepted = sum(item["accepted_drafts"] for item in trace)
    if fields["windows"] != windows or emitted != 16 or record["finish"] != "length":
        raise SystemExit(f"{name}: timing windows/prefix trace/request length disagree")
    if accepted != record.get("drafts_accepted", 0):
        raise SystemExit(f"{name}: per-round accepted drafts disagree with DONE counters")
    if spec > 0 and sum(item["window"] - 1 for item in trace) != record.get("drafts_offered", 0):
        raise SystemExit(f"{name}: per-round draft offers disagree with DONE counters")
    rows.append({
        "arm": name,
        "mtp_window": spec,
        "generated_tokens": emitted,
        "rounds": windows,
        "drafts_offered": record.get("drafts_offered", 0),
        "drafts_accepted": accepted,
        "drafts_rejected": record.get("drafts_offered", 0) - accepted,
        "acceptance_ratio": accepted / record["drafts_offered"] if record.get("drafts_offered", 0) else None,
        "target_correction_or_bonus_tokens": sum(item["committed"] - item["accepted_drafts"] for item in trace),
        "emitted_tokens_per_round": [item["committed"] for item in trace],
        "accepted_drafts_per_round": [item["accepted_drafts"] for item in trace],
        "timing_ms_per_round": fields,
        "timing_source": "STRATA_DECODE_TIMING per-request line; instrumented correctness run, not timing confirmation",
        "token_ids_match_mtp_off": spec == 0 or all(c["token_ids_equal"] for c in data["comparisons"] if c["candidate"] == name),
        "persistent_state_and_shared_prefix_match_mtp_off": spec == 0 or all(
            c["final_state_equal"] and all(x["equal"] for x in c["matched_commit_boundaries"])
            for c in data["comparisons"] if c["candidate"] == name),
    })

if not all(row["token_ids_match_mtp_off"] and row["persistent_state_and_shared_prefix_match_mtp_off"] for row in rows):
    raise SystemExit("an MTP arm failed accepted-prefix state parity")
result = {
    "schema": 1,
    "model_repository": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "quantization": "IQ1_M",
    "prompt_tokens": 2048,
    "generated_tokens": 16,
    "kv_format": data["kv_format"],
    "prompt_sha256": data["prompt_sha256"],
    "service_binary_sha256": data["arms"][0]["engine_sha256"],
    "source_commit": "ebef974c83b0e7bb08645abeea1166120aed7f95",
    "diagnostic_environment": {"STRATA_DECODE_TIMING": "1"},
    "arms": rows,
    "supervision": {
        "status": supervisor["status"],
        "elapsed_seconds": supervisor["elapsed_s"],
        "minimum_host_gib": supervisor["minimum_available_bytes"] / 2**30,
        "minimum_admission_gib": supervisor["minimum_admission_available_bytes"] / 2**30,
        "floor_gib": supervisor["floor_bytes"] / 2**30,
        "samples": len(samples),
        "memory_events_max": events,
        "clock_policy": supervisor["clock_sampling"],
        "energy_scope": supervisor["energy_scope"],
    },
    "scope": "one instrumented 2048-token fixed-prompt correctness/state run; per-window timing breakdown is diagnostic only and does not estimate untraced performance",
}
(CAMPAIGN / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
