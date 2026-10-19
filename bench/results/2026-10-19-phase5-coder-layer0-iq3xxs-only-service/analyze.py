#!/usr/bin/env python3
"""Compare IQ3_XXS/IQ4_NL-only CPU Q8_1 route with the default service route."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARMS = ROOT / "supervised"
NAMES = ("control-v2", "mirror", "fixed-control", "fixed-mirror")


def load_arm(name):
    path = ARMS / name
    run = json.loads((path / "run/analysis.json").read_text())
    supervisor = json.loads((path / "supervisor/result.json").read_text())
    if supervisor["status"] != "pass" or supervisor["returncode"] != 0:
        raise RuntimeError(f"{name}: supervised run failed")
    if len(run["requests"]) != 4 or any(len(request["ids"]) != 16 for request in run["requests"]):
        raise RuntimeError(f"{name}: expected four 16-token requests")
    command = supervisor["command"]
    if name in ("mirror", "fixed-mirror"):
        selector_at = command.index("--cpu-q8-1-pair") + 1
        if command[selector_at] != "iq3_xxs/iq4_nl":
            raise RuntimeError(f"{name}: selector mismatch: {command[selector_at]}")
    elif "--cpu-q8-1-pair" in command or "--cpu-q8-1-dot" in command:
        raise RuntimeError(f"{name}: control unexpectedly enables Q8_1")

    event_max = {key: 0 for key in ("low", "high", "max", "oom", "oom_kill")}
    for line in (path / "supervisor/memory.jsonl").read_text().splitlines():
        for group in json.loads(line).get("cgroups", []):
            if group.get("max_bytes") is None:
                continue
            for key, value in group.get("memory_events", {}).items():
                if key in event_max:
                    event_max[key] = max(event_max[key], value)
    return {
        "binary_sha256": run["binary_sha256"],
        "selector": "iq3_xxs/iq4_nl" if name in ("mirror", "fixed-mirror") else "default",
        "elapsed_s": supervisor["elapsed_s"],
        "minimum_host_available_gib": supervisor["minimum_available_bytes"] / 2**30,
        "minimum_admission_available_gib": supervisor["minimum_admission_available_bytes"] / 2**30,
        "maximum_cgroup_events": event_max,
        "requests": run["requests"],
        "raw_analysis": run,
    }


arms = {name: load_arm(name) for name in NAMES}
hashes = {arm["binary_sha256"] for arm in arms.values()}
if len(hashes) != 1:
    raise RuntimeError(f"binary mismatch across arms: {sorted(hashes)}")

comparisons = {}
for policy, control_name, mirror_name in (
    ("adaptive", "control-v2", "mirror"),
    ("fixed", "fixed-control", "fixed-mirror"),
):
    control = arms[control_name]["requests"]
    mirror = arms[mirror_name]["requests"]
    rows = []
    for left, right in zip(control, mirror):
        if left["name"] != right["name"] or len(left["ids"]) != len(right["ids"]):
            raise RuntimeError(f"{policy}: request mismatch")
        keys = sorted(set(left["state"]) & set(right["state"]))
        rows.append({
            "name": left["name"],
            "prompt_tokens": left["prompt_tokens"],
            "token_differences": sum(a != b for a, b in zip(left["ids"], right["ids"])),
            "state_equal_fields": [key for key in keys if left["state"][key] == right["state"][key]],
            "state_different_fields": [key for key in keys if left["state"][key] != right["state"][key]],
        })
    comparisons[policy] = rows
    for row in rows:
        print(policy, row["name"], "token differences", row["token_differences"],
              "state differences", len(row["state_different_fields"]))

model = json.loads((ROOT.parent / "2026-10-19-phase5-coder-layer0-iq3xxs-q8_1-mirror/artifact-identity.json").read_text())["model"]
report = {
    "experiment": "same-day format-pair-only diagnostic; not a qualification or performance comparison",
    "source_commit": "20810357",
    "source_overlay_sha256": "38d00c26fb480553669efa63bda5afeaae13a74445a3b407608b32fdc4fe052a",
    "binary_sha256": next(iter(hashes)),
    "model": model,
    "route_scope": "Only CPU-owned expert dispatches with IQ3_XXS gate/up and IQ4_NL down use Q8_1; all other pairs retain the default route. Selector covers eligible layers, not one layer only.",
    "profile": "prompt-cache=0, spec=2, suffix-draft=0, 8K context, 28-GiB MemoryMax, dynamic clocks",
    "accepted_drafts": "0 of 0 on every request in all four arms",
    "arms": arms,
    "comparisons": comparisons,
    "interpretation": "This format-pair-only change still changes persistent-state fingerprints and some output IDs. It does not isolate one layer, establish a quality result, or qualify CPU/GPU migration. Timings are retained as run metadata only; clocks were dynamic and the cell was designed for correctness/state diagnosis.",
}
(ROOT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"wrote {ROOT / 'analysis.json'}")
