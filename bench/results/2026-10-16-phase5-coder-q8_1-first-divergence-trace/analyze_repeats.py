#!/usr/bin/env python3
"""Verify and summarize the repeated randomized Coder route-trace pairs."""
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def bits(values):
    return struct.pack(f"<{len(values)}f", *values)


def load_rows(pair, route):
    lines = (pair / route / "result/layer1.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines[1:]]


def main():
    output = {"schema": 1, "pairs": []}
    reference_prompts = None
    min_available = None
    for index in range(1, 5):
        pair = ROOT / f"pair{index}"
        campaign = json.loads((pair / "campaign.json").read_text())
        routes = {route: load_rows(pair, route) for route in ("default", "cuda_mirror")}
        a, b = routes["default"], routes["cuda_mirror"]
        if len(a) != 192 or len(b) != 192:
            raise RuntimeError(f"pair{index}: expected 192 rows in each capture")
        if [r["dispatch"] for r in a] != [r["dispatch"] for r in b]:
            raise RuntimeError(f"pair{index}: dispatch rows do not align")
        first = next(((x, y) for x, y in zip(a, b)
                      if x["layer"] != y["layer"] or x["ids"] != y["ids"] or
                      x["route_kind"] != y["route_kind"] or
                      bits(x["activation"]) != bits(y["activation"])), None)
        if first is None:
            raise RuntimeError(f"pair{index}: no divergence in captured window")
        before_a = next(r for r in a if r["dispatch"] == 1393)
        before_b = next(r for r in b if r["dispatch"] == 1393)
        after_a = next(r for r in a if r["dispatch"] == 1394)
        after_b = next(r for r in b if r["dispatch"] == 1394)
        delta = [abs(x - y) for x, y in zip(after_a["activation"], after_b["activation"])]
        analyses = {route: json.loads((pair / route / "result/analysis.json").read_text())
                    for route in ("default", "cuda_mirror")}
        prompts = analyses["default"]["prompt_sha256"]
        if prompts != analyses["cuda_mirror"]["prompt_sha256"]:
            raise RuntimeError(f"pair{index}: prompt hashes differ by route")
        if reference_prompts is None:
            reference_prompts = prompts
        elif prompts != reference_prompts:
            raise RuntimeError(f"pair{index}: prompts differ between pairs")
        token_differences = []
        for left, right in zip(analyses["default"]["requests"], analyses["cuda_mirror"]["requests"]):
            if left["name"] != right["name"]:
                raise RuntimeError(f"pair{index}: request order differs")
            token_differences.append({"name": left["name"],
                                      "differing_positions": sum(x != y for x, y in zip(left["ids"], right["ids"])),
                                      "positions": max(len(left["ids"]), len(right["ids"]))})
        arm_results = {}
        for route in ("default", "cuda_mirror"):
            supervisor = json.loads((pair / route / "supervisor/result.json").read_text())
            if supervisor["status"] != "pass":
                raise RuntimeError(f"pair{index}/{route}: supervisor did not pass")
            available = supervisor["minimum_available_bytes"]
            admission = supervisor["minimum_admission_available_bytes"]
            min_available = min(min_available, available, admission) if min_available is not None else min(available, admission)
            arm_results[route] = {"status": supervisor["status"],
                                  "minimum_available_bytes": available,
                                  "minimum_admission_available_bytes": admission,
                                  "memory_samples": len((pair / route / "supervisor/memory.jsonl").read_text().splitlines())}
        result = {
            "pair": index,
            "seed": campaign["seed"],
            "order": campaign["order"],
            "first_divergence": {"dispatch": first[0]["dispatch"], "layer": first[0]["layer"],
                                 "ids_equal": first[0]["ids"] == first[1]["ids"],
                                 "owners_equal": first[0]["route_kind"] == first[1]["route_kind"]},
            "preceding_dispatch_1393_activation_equal": bits(before_a["activation"]) == bits(before_b["activation"]),
            "dispatch_1394_activation": {"max_absolute_difference": max(delta),
                                          "relative_l1": sum(delta) / sum(abs(x) for x in after_a["activation"])},
            "token_differences": token_differences,
            "arms": arm_results,
        }
        if result["first_divergence"] != {"dispatch": 1394, "layer": 2, "ids_equal": True, "owners_equal": True}:
            raise RuntimeError(f"pair{index}: first-divergence contract changed")
        if not result["preceding_dispatch_1393_activation_equal"]:
            raise RuntimeError(f"pair{index}: preceding activation is not bitwise equal")
        output["pairs"].append(result)
    output["model"] = "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M"
    output["prompt_sha256"] = reference_prompts
    output["minimum_host_or_admission_availability_bytes"] = min_available
    path = ROOT / "repeat-analysis.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"pairs": len(output["pairs"]), "minimum_availability_gib": min_available / 2**30,
                      "first_divergences": [p["first_divergence"] for p in output["pairs"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
