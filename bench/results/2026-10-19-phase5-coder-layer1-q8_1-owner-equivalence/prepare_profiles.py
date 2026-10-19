#!/usr/bin/env python3
"""Build equal-size profiles differing only in seven layer-1 Q8_1 targets."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import make_profile

BASE = ROOT / "data/expert-profile-coder.bin"
ROUTES = (ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/"
          "all-16-positions-three-arm-wildcard/cpu_default/result/routes-all-layers.jsonl")
TARGETS = [(1, expert) for expert in (205, 101, 32, 11, 95, 18, 165)]
CACHE_PREFIX = 3000


def main():
    base = make_profile.read_profile(BASE, 256)
    lines = ROUTES.read_text().splitlines()
    rows = [json.loads(line) for line in lines[1:]]
    if json.loads(lines[0]).get("format") != "strata-moe-dispatch-v3" or len(rows) != 768:
        raise RuntimeError("expected the pinned 16-position, 48-layer route capture")
    used = {(int(row["layer"]), int(expert)) for row in rows for expert in row["ids"]}
    if any(pair in base[:CACHE_PREFIX] for pair in TARGETS):
        raise RuntimeError("a target expert is already resident in the control prefix")
    fillers = [pair for pair in reversed(base[:CACHE_PREFIX])
               if pair not in used and pair not in TARGETS][:len(TARGETS)]
    if len(fillers) != len(TARGETS):
        raise RuntimeError("could not find enough unused filler experts")
    control = base[:CACHE_PREFIX] + fillers
    candidate = base[:CACHE_PREFIX] + TARGETS
    if len(control) != CACHE_PREFIX + len(TARGETS) or len(candidate) != len(control):
        raise RuntimeError("profile slot counts do not match")
    if control[:CACHE_PREFIX] != candidate[:CACHE_PREFIX]:
        raise RuntimeError("the common cache prefix changed")
    if any(pair in used for pair in fillers):
        raise RuntimeError("a filler appeared in the captured route trace")
    for name, ranked in (("control", control), ("gpu-layer1", candidate)):
        path = HERE / f"profile-{name}.bin"
        make_profile.write_profile(path, ranked, 256)
        if make_profile.read_profile(path, 256) != ranked:
            raise RuntimeError(f"profile round-trip failed: {name}")
    record = {
        "base_profile": str(BASE.relative_to(ROOT)),
        "base_profile_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "source_routes": str(ROUTES.relative_to(ROOT)),
        "source_routes_sha256": hashlib.sha256(ROUTES.read_bytes()).hexdigest(),
        "captured_route_rows": len(rows),
        "base_cache_prefix_slots": CACHE_PREFIX,
        "requested_slots_each_profile": CACHE_PREFIX + len(TARGETS),
        "common_prefix_sha256": hashlib.sha256(
            b"".join((layer.to_bytes(2, "little") + expert.to_bytes(2, "little"))
                    for layer, expert in control[:CACHE_PREFIX])).hexdigest(),
        "targets": [list(pair) for pair in TARGETS],
        "fillers": [list(pair) for pair in fillers],
        "fillers_absent_from_all_16x48_captured_routes": True,
        "profiles": {
            name: {"path": f"profile-{name}.bin",
                   "sha256": hashlib.sha256((HERE / f"profile-{name}.bin").read_bytes()).hexdigest()}
            for name in ("control", "gpu-layer1")
        },
        "limitations": [
            "route trace covers generated positions, not every prompt-prefill expert",
            "runtime READY and residency verification must confirm realized cache geometry",
        ],
    }
    (HERE / "profile-design.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
