#!/usr/bin/env python3
"""Recompute Q2_0 speculation-window graph capture backing observations."""
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BY_RUN = []
for i in range(6):
    d = ROOT / f"run-{i:02d}-spec{2 if i in (0, 3, 4) else 4}"
    cfg = json.loads((d / "server-config.json").read_text())
    spec = int(cfg["args"][cfg["args"].index("--spec") + 1])
    client = json.loads((d / "result.json").read_text())
    assert client["checks"][0]["status"] == "pass"
    assert client["checks"][0]["usage"]["prompt_tokens"] == 31
    assert client["checks"][0]["usage"]["completion_tokens"] == 24
    output_text = client["checks"][0]["text"]
    engine_lines = (d / "engine.log").read_text(errors="replace").splitlines()
    graph_times, graph_count = [], 0
    for line in engine_lines:
        if line.startswith("strata integration: "):
            event = json.loads(line[len("strata integration: "):])
            if event.get("kind") == "graph_instantiate":
                graph_times.append(event["monotonic_s"])
                graph_count += event["count"]
    assert graph_count > 0
    samples = [json.loads(line) for line in (d / "nvmap-clients.jsonl").read_text().splitlines() if line]
    pids = {c["pid"] for row in samples for c in row["clients"]
            if c["process"] == "strata" and c["size_bytes"] > 1 << 30}
    assert len(pids) == 1, f"expected one model process in NVMap, found {pids}"
    pid = next(iter(pids))
    timeline = []
    for row in samples:
        values = [c["size_bytes"] for c in row["clients"] if c["pid"] == pid]
        if values:
            timeline.append((row["monotonic_s"], sum(values)))
    pre = [size for t, size in timeline if t < min(graph_times)]
    post = [size for _, size in timeline[-20:]]
    assert len(pre) >= 20 and len(post) == 20
    pre_bytes, post_bytes = int(statistics.median(pre[-20:])), int(statistics.median(post))
    supervisor_dir = d / ("supervisor-retry2" if i == 0 else "supervisor")
    supervisor = json.loads((supervisor_dir / "result.json").read_text())
    assert supervisor["status"] == "pass"
    mem = [json.loads(line) for line in (supervisor_dir / "memory.jsonl").read_text().splitlines() if line]
    caps = [x["max_bytes"] - x["current_bytes"] for row in mem for x in row["cgroups"]
            if x.get("max_bytes") is not None]
    assert caps
    output_sha = hashlib.sha256(output_text.encode()).hexdigest()
    BY_RUN.append({"run": i, "pair": i // 2, "spec": spec, "pid": pid,
                   "request": client["checks"][0], "output_sha256": output_sha,
                   "nvmap_sample_rows": len(samples), "process_nvmap_samples": len(timeline),
                   "graph_instantiations": graph_count, "graph_call_monotonic_s": graph_times,
                   "baseline_plateau_samples": len(pre[-20:]), "baseline_nvmap_bytes": pre_bytes,
                   "post_plateau_samples": len(post), "post_nvmap_bytes": post_bytes,
                   "capture_interval_delta_bytes": post_bytes - pre_bytes,
                   "minimum_host_available_bytes": min(row["available_bytes"] for row in mem),
                   "minimum_cgroup_headroom_bytes": min(caps),
                   "cgroup_oom_event_max": max(x.get("memory_events", {}).get("oom", 0) +
                                                x.get("memory_events", {}).get("oom_kill", 0)
                                                for row in mem for x in row["cgroups"]
                                                if x.get("max_bytes") is not None),
                   "supervisor_status": supervisor["status"]})

pairs = []
for i in range(3):
    lo, hi = BY_RUN[2 * i:2 * i + 2]
    assert lo["spec"] != hi["spec"]
    pairs.append({"pair": i, "spec2_run": lo if lo["spec"] == 2 else hi,
                  "spec4_run": hi if hi["spec"] == 4 else lo,
                  "spec4_minus_spec2_capture_delta_bytes":
                      (hi if hi["spec"] == 4 else lo)["capture_interval_delta_bytes"] -
                      (lo if lo["spec"] == 2 else hi)["capture_interval_delta_bytes"]})
assert len({r["output_sha256"] for r in BY_RUN}) == 1
assert all(r["supervisor_status"] == "pass" and r["cgroup_oom_event_max"] == 0 for r in BY_RUN)

report = {"date": "2026-10-11", "model": "Q2_0 native Orin validation artifacts",
          "scope": "configuration-level NVMap backing change over first-request graph capture/instantiation; not isolated executable bytes",
          "pair_order": [r["spec"] for r in BY_RUN], "runs": BY_RUN, "pairs": pairs,
          "spec2_capture_interval_deltas_bytes": [r["capture_interval_delta_bytes"] for r in BY_RUN if r["spec"] == 2],
          "spec4_capture_interval_deltas_bytes": [r["capture_interval_delta_bytes"] for r in BY_RUN if r["spec"] == 4],
          "spec4_minus_spec2_paired_deltas_bytes": [p["spec4_minus_spec2_capture_delta_bytes"] for p in pairs],
          "same_output_all_runs": True,
          "limitations": ["NVMap interval includes adjacent synchronous allocations and other process work.",
                          "Only process-owned NVMap IOVMM backing is measured; other driver-private memory is outside scope.",
                          "Three pairs are a screening result, not a seven-pair performance confirmation."]}
(ROOT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
for r in BY_RUN:
    print(r["run"], "spec", r["spec"], "graphs", r["graph_instantiations"],
          "delta", r["capture_interval_delta_bytes"], "minAvail", r["minimum_host_available_bytes"])
print("paired spec4-spec2 deltas", report["spec4_minus_spec2_paired_deltas_bytes"])
