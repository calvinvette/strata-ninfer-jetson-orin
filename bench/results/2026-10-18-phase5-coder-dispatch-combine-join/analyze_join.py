#!/usr/bin/env python3
"""Join the same-service CPU expert and verifier combine captures for dispatch 1393."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture"
ANALYZER = ROOT / "bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace"
sys.path.insert(0, str(ANALYZER))
from analyze_combined_moe import read_combined, read_jsonl  # noqa: E402

OUT = Path(__file__).with_name("analysis.json")
DISPATCH = 1393
reports = {}
for arm in ("default", "cuda_mirror"):
    run = SOURCE / arm / "result"
    layer, combined = read_combined(run / "combined-moe.bin")
    assert layer == 1 and combined, (arm, layer, len(combined))
    route = read_jsonl(run / "layer1.jsonl")
    first = route[:2]
    assert [(x["dispatch"], x["layer"], x["row"], x["stream_row"], x["n_tok"])
            for x in first] == [(1392, 0, 0, 1392, 1), (DISPATCH, 1, 0, DISPATCH, 1)], arm
    joined = next(x for x in route if x["dispatch"] == DISPATCH and x["layer"] == 1)
    ffn = combined[0]
    assert (ffn["position"], ffn["token"]) == (511, 271), (arm, ffn["position"], ffn["token"])
    assert joined["n_tok"] == 1 and joined["row"] == 0

    cpu_records = [x for x in read_jsonl(run / "cpu-outputs.jsonl")
                   if x["dispatch"] == DISPATCH and x["layer"] == 1]
    expected = {(row, joined["ids"][row]) for row, owner in enumerate(joined["route_kind"]) if owner == -1}
    actual = {(x["row"], x["expert"]) for x in cpu_records}
    assert actual == expected and len(actual) == 4, (arm, sorted(actual), sorted(expected))
    requests = json.loads((run / "requests.json").read_text())["requests"]
    assert requests[0]["name"] == "short-512" and len(requests[0]["ids"]) == 16
    reports[arm] = {"route": joined, "cpu_outputs": {x["expert"]: x["output"] for x in cpu_records},
                    "combined_first": ffn, "initial_request": requests[0]}

a, b = reports["default"], reports["cuda_mirror"]
assert a["route"]["activation"] == b["route"]["activation"]
assert a["route"]["ids"] == b["route"]["ids"]
assert a["route"]["route_kind"] == b["route"]["route_kind"]
assert (a["combined_first"]["position"], a["combined_first"]["token"]) == (
       b["combined_first"]["position"], b["combined_first"]["token"])
assert a["initial_request"]["ids"] == b["initial_request"]["ids"]

cpu_deltas = []
for expert in sorted(a["cpu_outputs"]):
    x, y = a["cpu_outputs"][expert], b["cpu_outputs"][expert]
    assert len(x) == len(y)
    delta = [float(u) - float(v) for u, v in zip(x, y)]
    cpu_deltas.append({"expert": expert, "different_values": sum(u != v for u, v in zip(x, y)),
                       "elements": len(x), "relative_l1": math.fsum(abs(v) for v in delta) /
                       max(math.fsum(abs(float(v)) for v in x), 1e-30)})
fa, fb = a["combined_first"]["ffn_y"], b["combined_first"]["ffn_y"]
combined_delta = [float(x) - float(y) for x, y in zip(fa, fb)]
summary = {
    "input_capture_directory": str(SOURCE.relative_to(ROOT)),
    "join": {"dispatch": DISPATCH, "layer": 1, "verifier_position": 511,
             "input_token": 271, "route_n_tok": 1, "route_row": 0,
             "cpu_output_experts": sorted(a["cpu_outputs"]),
             "method": "same-service ordered callback capture: layer-0 dispatch 1392 is immediately followed by layer-1 dispatch 1393; the selected layer-1 STGDIAG4 capture is the first verifier window and records position 511/token 271. CPU-output rows are keyed to dispatch/layer and verified against the captured route IDs and CPU owner slots."},
    "cross_arm_controls": {"activation_bitwise_equal": True, "expert_ids_equal": True,
                           "route_owners_equal": True, "combined_position_token_equal": True,
                           "initial_request_output_equal": True},
    "cpu_expert_output_deltas": cpu_deltas,
    "combined_ffn_y": {"different_values": sum(x != y for x, y in zip(fa, fb)),
                        "elements": len(fa), "max_abs_delta": max(map(abs, combined_delta)),
                        "relative_l1": math.fsum(abs(x) for x in combined_delta) /
                        max(math.fsum(abs(float(x)) for x in fa), 1e-30)},
    "interpretation": "The four CPU-owned expert rows and the later weighted-combine output are now joined to the same first verifier row in each service. This links a route-dependent arithmetic difference to a post-combine difference on the same input position. It does not isolate each expert's weighted contribution or prove this difference is the only cause of persistent-state/continuation divergence.",
}
OUT.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
