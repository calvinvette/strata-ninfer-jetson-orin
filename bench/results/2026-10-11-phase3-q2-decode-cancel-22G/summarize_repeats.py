#!/usr/bin/env python3
"""Validate and summarize the three successful Q2_0 decode-cancel runs."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
report = {"scope": "22 GiB MemoryMax; supervisor six-GiB floor; Q2_0 decode cancel + recovery",
          "runs": []}
for n in (3, 4, 5):
    d = ROOT / f"rerun{n}"
    client = json.loads((d / "result.json").read_text())
    supervisor = json.loads((d / "supervisor/result.json").read_text())
    assert supervisor["status"] == "pass"
    assert all(c["status"] == "pass" for c in client["checks"])
    rows = [json.loads(s) for s in (d / "supervisor/memory.jsonl").read_text().splitlines() if s]
    capped = [c["max_bytes"] - c["current_bytes"] for r in rows for c in r["cgroups"] if c.get("max_bytes")]
    events = []
    for line in (d / "engine.log").read_text(errors="replace").splitlines():
        marker = "strata integration: "
        if marker not in line:
            continue
        try:
            event = json.loads(line.split(marker, 1)[1])
        except json.JSONDecodeError:
            continue
        if event.get("kind") in ("allocate", "free"):
            events.append(event)
    allocations = {(e["owner"], e["allocation"]): e for e in events if e["kind"] == "allocate"}
    frees = {(e["owner"], e["allocation"]): e for e in events if e["kind"] == "free"}
    persistent = {k for k in allocations if k[0] == "weight-arena"}
    assert allocations.keys() - persistent == frees.keys()
    assert not frees.keys() - allocations.keys()
    counts = Counter((e["owner"], e["kind"]) for e in events)
    report["runs"].append({
        "run": n,
        "client_checks": client["checks"],
        "supervisor": "pass",
        "minimum_host_available_bytes": min(r["available_bytes"] for r in rows),
        "minimum_cgroup_headroom_bytes": min(capped) if capped else None,
        "cgroup_oom_events_max": max((c.get("memory_events", {}).get("oom", 0) +
                                       c.get("memory_events", {}).get("oom_kill", 0))
                                      for r in rows for c in r["cgroups"] if c.get("max_bytes")),
        "owner_events": {f"{owner}:{kind}": count for (owner, kind), count in sorted(counts.items())},
        "released_owner_pairs": len(allocations.keys() - persistent),
        "persistent_weight_arena_bytes": sum(e["requested_bytes"] for k, e in allocations.items()
                                             if k in persistent),
    })
(ROOT / "repeat-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
for r in report["runs"]:
    print(r["run"], "pass", "host_min", r["minimum_host_available_bytes"],
          "cgroup_headroom_min", r["minimum_cgroup_headroom_bytes"],
          "released_pairs", r["released_owner_pairs"], "persistent", r["persistent_weight_arena_bytes"])
