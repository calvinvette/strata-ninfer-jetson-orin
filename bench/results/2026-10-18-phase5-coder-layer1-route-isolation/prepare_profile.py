#!/usr/bin/env python3
"""Move the four observed CPU-routed layer-1 experts into unchanged 3,000-slot capacity."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_profile

OUT = Path(__file__).resolve().parent
base_path = ROOT / "data/expert-profile-coder.bin"
route_path = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/retry-start0/cpu_default/result/layer1.jsonl"
base = make_profile.read_profile(base_path, 256)
rows = [json.loads(line) for line in route_path.read_text().splitlines()[1:]]
first_window = {row["layer"]: row for row in rows if 0 <= row["dispatch"] <= 47}
assert len(first_window) == 48 and set(first_window) == set(range(48))
row = first_window[1]
assert row["dispatch"] == 1 and row["row"] == 0 and row["n_tok"] == 1
# Keep every first-window residency unchanged except the four captured layer-1 CPU misses.
targets = [(1, row["ids"][i]) for i, owner in enumerate(row["route_kind"]) if owner == -1]
assert targets == [(1, 205), (1, 101), (1, 32), (1, 11), (1, 95), (1, 18), (1, 165)], targets
assert all(pair not in base[:3000] for pair in targets)
used = {(layer, expert) for layer, dispatch in first_window.items() for expert in dispatch["ids"]}
evictions = []
for pair in reversed(base[:3000]):
    if pair not in used and pair not in targets:
        evictions.append(pair)
        if len(evictions) == len(targets):
            break
assert len(evictions) == len(targets)
# Replace only unused bottom-cache entries, preserving ordering and membership for every other pair.
ranked = base[:3000 - len(targets)] + targets + [p for p in base[3000 - len(targets):] if p not in targets]
assert len(ranked) == len(base) and ranked[:3000 - len(targets)] == base[:3000 - len(targets)]
assert set(ranked[:3000]) == set(base[:3000]) - set(evictions) | set(targets)
profile = OUT / "layer1-gpu-profile.bin"
make_profile.write_profile(profile, ranked, 256)
assert make_profile.read_profile(profile, 256) == ranked
meta = {"base_profile": str(base_path.relative_to(ROOT)),
        "base_profile_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        "base_slots": 3000, "targets": [list(x) for x in targets],
        "evicted_unused_pairs": [list(x) for x in evictions],
        "source_window_dispatches": [0, 47],
        "target_dispatch": row["dispatch"],
        "first_window_used_pairs_unchanged_except_targets": True,
        "output_profile": profile.name,
        "output_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
        "source_capture": str(route_path.relative_to(ROOT))}
(OUT / "profile-design.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta, indent=2))
