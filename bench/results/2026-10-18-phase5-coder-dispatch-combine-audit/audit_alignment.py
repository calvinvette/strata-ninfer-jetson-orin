#!/usr/bin/env python3
"""Audit whether the existing route/CPU and post-combine captures can be joined."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture"
sys.path.insert(0, str(ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace"))
from analyze_combined_moe import read_combined, read_jsonl  # noqa: E402

out = Path(__file__).with_name("alignment-audit.json")
summary = {"source": str(SOURCE.relative_to(ROOT)), "arms": {},
           "same_verifier_row_join_proven": False,
           "reason": "The route capture starts after 1,392 rows and records dispatch/row/stream_row but no absolute position or token ID. The STGDIAG4 capture starts at position 511/token 271. The retained raw records do not provide a shared row key, and the skipped route prefix needed to map the dispatch counter to an absolute verifier position is absent.",
           "withdrawal": "The 2026-10-18 report at the former *-dispatch-combine-join path incorrectly equated dispatch 1393/layer 1 with the first STGDIAG4 row. That assertion is withdrawn. The existing paired captures remain separate diagnostics until a new run records shared position/token metadata."}
for arm in ("default", "cuda_mirror"):
    run = SOURCE / arm / "result"
    layer, combined = read_combined(run / "combined-moe.bin")
    route = read_jsonl(run / "layer1.jsonl")
    cpu = read_jsonl(run / "cpu-outputs.jsonl")
    assert layer == 1 and combined
    assert [(x["dispatch"], x["layer"], x["row"], x["stream_row"], x["n_tok"])
            for x in route[:2]] == [(1392, 0, 0, 1392, 1), (1393, 1, 0, 1393, 1)]
    selected = next(x for x in route if x["dispatch"] == 1393 and x["layer"] == 1)
    cpu_rows = [x for x in cpu if x["dispatch"] == 1393 and x["layer"] == 1]
    expected = {(i, selected["ids"][i]) for i, owner in enumerate(selected["route_kind"]) if owner == -1}
    assert {(x["row"], x["expert"]) for x in cpu_rows} == expected
    requests = json.loads((run / "requests.json").read_text())["requests"]
    summary["arms"][arm] = {
        "route_capture_start_row": 1392,
        "first_saved_route_record": {k: route[0][k] for k in ("dispatch", "layer", "row", "stream_row", "n_tok")},
        "selected_dispatch": {k: selected[k] for k in ("dispatch", "layer", "row", "stream_row", "n_tok", "ids", "route_kind")},
        "cpu_output_rows_match_selected_route": True,
        "route_records_have_position_or_token_id": any(k in selected for k in ("position", "token", "token_id")),
        "combined_first_record": {"position": combined[0]["position"], "token": combined[0]["token"]},
        "combined_rows": len(combined),
        "request_order": [x["name"] for x in requests],
    }
out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
