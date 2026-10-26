#!/usr/bin/env python3
"""Join captured routed expert rows to the independent scalar Q2_0 oracle."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent / "evidence"
CAPTURES = {1: EVIDENCE / "moe-layer1-pos2047", 2: EVIDENCE / "moe-layer2-pos2047"}
OUTPUTS = {1: EVIDENCE / "oracle-layer1", 2: EVIDENCE / "oracle-layer2"}
GGUF = Path.home() / "models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf"
sys.path.insert(0, str(ROOT / "tools/integration"))
from q2_0_expert_oracle import run as q2_oracle

INPUT_HEADER = struct.Struct("<8sIIIIQq8i")
ROW_HEADER = struct.Struct("<8sIIIIQqii")
EXPERTS = {1: (97, 74, 70), 2: (372, 357)}


def error_metrics(reference: tuple[float, ...], actual: tuple[float, ...]) -> dict:
    delta = [b - a for a, b in zip(reference, actual)]
    norm = sum(x * x for x in reference) ** 0.5
    return {
        "count": len(reference),
        "different": sum(a != b for a, b in zip(reference, actual)),
        "relative_l2": (sum(x * x for x in delta) ** 0.5) / max(norm, 1e-300),
        "max_abs": max(map(abs, delta), default=0.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    layer = args.layer
    capture = CAPTURES[layer]
    output = OUTPUTS[layer]
    experts = EXPERTS[layer]
    output.mkdir(parents=True, exist_ok=True)
    result = {"schema": 1, "layer": layer, "position": 2047, "experts": []}
    route = json.loads((capture / f"cpu-miss.layer{layer}.route").read_text().splitlines()[1])
    route_ids = route["ids"]
    for arm in ("cpu-miss", "ninfer-staged"):
        raw_input = (capture / f"{arm}.layer{layer}.input").read_bytes()
        ih = INPUT_HEADER.unpack_from(raw_input)
        if ih[0] != b"STMOINP1" or ih[2] != layer or ih[3] != 1 or ih[5] != 2560 or ih[6] != 2047:
            raise ValueError(f"{arm}: unexpected layer-2 activation capture header {ih}")
        activation = raw_input[INPUT_HEADER.size:]
        if len(activation) != 2560 * 4:
            raise ValueError(f"{arm}: captured activation has {len(activation)} bytes")
        activation_path = output / f"{arm}.activation.f32"
        activation_path.write_bytes(activation)
        raw_parts = (capture / f"{arm}.layer{layer}.parts").read_bytes()
        ph = ROW_HEADER.unpack_from(raw_parts)
        if ph[0] != b"STMPART2" or ph[2] != layer or ph[3] != 10 or ph[5] != 2560 or ph[6] != 2047:
            raise ValueError(f"{arm}: unexpected layer-2 parts capture header {ph}")
        expert_results = []
        for rank, expert in enumerate(route_ids):
            if expert not in experts:
                continue
            start = ROW_HEADER.size + rank * 2560 * 4
            actual = struct.unpack_from("<2560f", raw_parts, start)
            part_path = output / f"{arm}.expert{expert}.part.f32"
            part_path.write_bytes(struct.pack("<2560f", *actual))
            oracle_path = output / f"{arm}.expert{expert}.oracle.f64"
            oracle_info = q2_oracle(GGUF, activation_path, layer=layer, expert=expert,
                                    output_f64=oracle_path)
            reference = struct.unpack("<2560d", oracle_path.read_bytes())
            metric = error_metrics(reference, actual)
            q8_path = output / f"{arm}.expert{expert}.q8_1-oracle.f64"
            q8_info = q2_oracle(GGUF, activation_path, layer=layer, expert=expert,
                                output_f64=q8_path, q8_1=True)
            q8_reference = struct.unpack("<2560d", q8_path.read_bytes())
            expert_results.append({
                "rank": rank, "expert": expert, "oracle": oracle_info,
                "part_vs_f64_oracle": metric,
                "q8_1_runtime_contract_oracle": q8_info,
                "part_vs_q8_1_runtime_contract_oracle": error_metrics(q8_reference, actual),
                "part_sha256": hashlib.sha256(part_path.read_bytes()).hexdigest(),
                "oracle_f64_sha256": hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
                "q8_1_oracle_f64_sha256": hashlib.sha256(q8_path.read_bytes()).hexdigest(),
            })
        result["experts"].append({
            "arm": arm,
            "activation_sha256": hashlib.sha256(activation).hexdigest(),
            "activation_file": activation_path.name,
            "expert_results": expert_results,
        })
    path = output / "analysis.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
