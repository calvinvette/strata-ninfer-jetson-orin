#!/usr/bin/env python3
"""Summarize the bounded route pair and same-activation expert checks."""
import json
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAIR = ROOT / "pair1"
OPERATORS = ROOT / "operator-checks/results"
PATTERN = re.compile(
    r"layer 1 expert\s+(\d+)\s+(\S+)\s+/\s*(\S+)\s+blob\s+(\d+)"
    r"\s+cpu rel\s+([^ ]+)\s+gpu rel\s+([^ ]+)\s+cpu-gpu\s+([^ ]+)"
    r"\s+\((\d+)/(\d+) words differ\)"
)


def read_capture(route: str) -> list[dict]:
    path = PAIR / route / "result/layer1.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()[1:]]


def float_bytes(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def main() -> int:
    default_rows = read_capture("default")
    mirror_rows = read_capture("cuda_mirror")
    if len(default_rows) != 192 or len(mirror_rows) != 192:
        raise RuntimeError("expected the two 192-row bounded all-layer captures")
    if [r["dispatch"] for r in default_rows] != [r["dispatch"] for r in mirror_rows]:
        raise RuntimeError("the captured dispatch windows do not align")
    first = None
    for a, b in zip(default_rows, mirror_rows):
        if (a["layer"], a["ids"], a["route_kind"], float_bytes(a["activation"])) != (
                b["layer"], b["ids"], b["route_kind"], float_bytes(b["activation"])):
            first = (a, b)
            break
    if first is None:
        raise RuntimeError("no route or activation divergence found in captured window")
    before = next(r for r in default_rows if r["dispatch"] == 1393)
    after = next(r for r in default_rows if r["dispatch"] == 1394)
    after_mirror = next(r for r in mirror_rows if r["dispatch"] == 1394)
    delta = [abs(float(a) - float(b)) for a, b in zip(after["activation"], after_mirror["activation"])]
    token_summaries = []
    default_analysis = json.loads((PAIR / "default/result/analysis.json").read_text())
    mirror_analysis = json.loads((PAIR / "cuda_mirror/result/analysis.json").read_text())
    for a, b in zip(default_analysis["requests"], mirror_analysis["requests"]):
        token_summaries.append({"name": a["name"], "token_differences": sum(x != y for x, y in zip(a["ids"], b["ids"]))})
    operator_rows = []
    for path in sorted(OPERATORS.glob("expert-*.txt")):
        match = PATTERN.search(path.read_text())
        if match is None:
            raise RuntimeError(f"could not parse operator output {path}")
        expert, gu, down, blob, cpu, gpu, delta_l1, diffs, total = match.groups()
        operator_rows.append({"expert": int(expert), "route": path.stem.rsplit("-", 1)[1],
                              "gate_up_type": gu, "down_type": down, "blob_bytes": int(blob),
                              "cpu_relative_l1": float(cpu), "gpu_relative_l1": float(gpu),
                              "cpu_gpu_relative_l1": float(delta_l1),
                              "cpu_gpu_bitwise_differences": int(diffs), "output_words": int(total)})
    supervisors = {}
    for route in ("default", "cuda_mirror"):
        result = json.loads((PAIR / route / "supervisor/result.json").read_text())
        supervisors[route] = {"status": result["status"],
                              "minimum_available_bytes": result.get("minimum_available_bytes"),
                              "minimum_admission_available_bytes": result.get("minimum_admission_available_bytes")}
    out = {
        "schema": 1,
        "model": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "capture_dispatch_range": [default_rows[0]["dispatch"], default_rows[-1]["dispatch"]],
        "first_divergence": {"dispatch": first[0]["dispatch"], "layer": first[0]["layer"],
                             "default_matches_mirror_activation": float_bytes(first[0]["activation"]) == float_bytes(first[1]["activation"]),
                             "default_matches_mirror_ids": first[0]["ids"] == first[1]["ids"],
                             "default_matches_mirror_owners": first[0]["route_kind"] == first[1]["route_kind"]},
        "preceding_cpu_route": {"dispatch": before["dispatch"], "layer": before["layer"],
                                "experts_and_owners": list(zip(before["ids"], before["route_kind"])),
                                "activation_bitwise_equal": float_bytes(before["activation"]) ==
                                    float_bytes(next(r for r in mirror_rows if r["dispatch"] == 1393)["activation"])},
        "first_differing_activation": {"dispatch": after["dispatch"], "layer": after["layer"],
                                       "max_absolute_difference": max(delta),
                                       "relative_l1": sum(delta) / sum(abs(float(x)) for x in after["activation"])},
        "cross_route_tokens": token_summaries,
        "supervisors": supervisors,
        "operator_checks": operator_rows,
    }
    (ROOT / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["first_divergence"], indent=2))
    print(json.dumps(out["first_differing_activation"], indent=2))
    print("operator checks:", len(operator_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
