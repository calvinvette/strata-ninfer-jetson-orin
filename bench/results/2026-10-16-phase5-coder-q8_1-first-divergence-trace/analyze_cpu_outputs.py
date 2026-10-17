#!/usr/bin/env python3
"""Join one service's routed activation and actual CPU expert output captures."""
import json
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAIR = ROOT / "pair5-cpu-output"
DISPATCH = 1393
LAYER = 1


def f32_bytes(values):
    return struct.pack(f"<{len(values)}f", *values)


def main():
    records = {}
    for route in ("default", "cuda_mirror"):
        result = PAIR / route / "result"
        analysis = json.loads((result / "analysis.json").read_text())
        lines = (result / "layer1.jsonl").read_text().splitlines()
        input_rows = [json.loads(line) for line in lines[1:]]
        inputs = [row for row in input_rows if row["dispatch"] == DISPATCH and row["layer"] == LAYER]
        if len(inputs) != 1:
            raise RuntimeError(f"{route}: expected one input at dispatch {DISPATCH}, found {len(inputs)}")
        output_lines = (result / "cpu-outputs.jsonl").read_text().splitlines()
        header = json.loads(output_lines[0])
        if header != {"format": "strata-moe-cpu-output-v1", "n_embd": 2560}:
            raise RuntimeError(f"{route}: unexpected output-capture header {header}")
        outputs = [json.loads(line) for line in output_lines[1:]]
        if any(row["dispatch"] != DISPATCH or row["layer"] != LAYER for row in outputs):
            raise RuntimeError(f"{route}: output capture contains a different dispatch")
        if analysis["captured_cpu_output_rows"] != len(outputs):
            raise RuntimeError(f"{route}: analysis row count does not match capture")
        records[route] = {"analysis": analysis, "input": inputs[0], "outputs": outputs}

    left, right = records["default"], records["cuda_mirror"]
    a, b = left["input"], right["input"]
    if f32_bytes(a["activation"]) != f32_bytes(b["activation"]):
        raise RuntimeError("the service activations are not bitwise equal")
    if a["ids"] != b["ids"] or a["route_kind"] != b["route_kind"]:
        raise RuntimeError("the service routed experts or owners differ")
    expected = [(expert, owner) for expert, owner in zip(a["ids"], a["route_kind"]) if owner < 0]
    left_by_expert = {row["expert"]: row for row in left["outputs"]}
    right_by_expert = {row["expert"]: row for row in right["outputs"]}
    if list(left_by_expert) != [expert for expert, _ in expected] or list(right_by_expert) != list(left_by_expert):
        raise RuntimeError("captured CPU outputs do not match the input's CPU-owned expert order")
    result_rows = []
    for expert, _owner in expected:
        x = left_by_expert[expert]["output"]
        y = right_by_expert[expert]["output"]
        if len(x) != 2560 or len(y) != 2560 or not all(math.isfinite(v) for v in x + y):
            raise RuntimeError(f"expert {expert}: invalid output vector")
        delta = [abs(v - w) for v, w in zip(x, y)]
        result_rows.append({"expert": expert, "elements": len(x),
                            "bitwise_differences": sum(v != w for v, w in zip(x, y)),
                            "max_absolute_difference": max(delta),
                            "relative_l1": sum(delta) / sum(abs(v) for v in x)})
    output = {
        "schema": 1,
        "model": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "dispatch": DISPATCH,
        "layer": LAYER,
        "activation_bitwise_equal": True,
        "expert_ids_and_owners_equal": True,
        "cpu_owned_experts": [expert for expert, _owner in expected],
        "actual_service_cpu_outputs_default_vs_cuda_mirror": result_rows,
        "service_token_differences_default_vs_cuda_mirror": [
            {"name": left_req["name"],
             "different_positions": sum(x != y for x, y in zip(left_req["ids"], right_req["ids"]))}
            for left_req, right_req in zip(left["analysis"]["requests"], right["analysis"]["requests"])],
        "supervisors": {
            route: json.loads((PAIR / route / "supervisor/result.json").read_text())["status"]
            for route in ("default", "cuda_mirror")},
        "interpretation": "The row delta is observed in the service's actual CPU output buffer. It localizes a real dispatch difference before the weighted combine; it does not alone prove the combined MoE output or later state is correct.",
    }
    path = ROOT / "cpu-output-analysis.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
