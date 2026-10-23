#!/usr/bin/env python3
"""Compare same-position verifier MoE inputs across three same-service requests."""
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = struct.Struct("<8sIIIIQq8i")
LAYERS = 48
WIDTH = 2560
REQUESTS = ("initial", "intermediate", "recovery")


def read_arm(path):
    data = path.read_bytes()
    offset = 0
    groups = []
    while offset < len(data):
        if len(data) - offset < HEADER.size:
            raise ValueError(f"{path}: truncated input header")
        magic, version, layer, rows, reserved, width, pos0, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STMOINP1" or version != 1 or reserved != 0 or width != WIDTH or rows != 1 or pos0 != 511:
            raise ValueError(f"{path}: invalid input record {(magic, version, layer, rows, width, pos0)}")
        size = rows * width * 4
        if layer < 0 or layer >= LAYERS or len(data) - offset < size:
            raise ValueError(f"{path}: invalid layer or truncated payload")
        payload = data[offset:offset + size]
        offset += size
        values = struct.unpack(f"<{WIDTH}f", payload)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{path}: non-finite input at layer {layer}")
        groups.append((layer, tokens[0], payload))
    if len(groups) != 3 * LAYERS:
        raise ValueError(f"{path}: expected {3 * LAYERS} records, got {len(groups)}")
    requests = []
    for index in range(3):
        chunk = groups[index * LAYERS:(index + 1) * LAYERS]
        if [row[0] for row in chunk] != list(range(LAYERS)):
            raise ValueError(f"{path}: request {index + 1} layers are missing, duplicated, or out of order")
        if {row[1] for row in chunk} != {271}:
            raise ValueError(f"{path}: request {index + 1} token IDs differ from expected prompt-tail token")
        requests.append({layer: payload for layer, _, payload in chunk})
    return requests


def compare(left, right):
    a = struct.unpack(f"<{WIDTH}f", left)
    b = struct.unpack(f"<{WIDTH}f", right)
    delta = [float(x) - float(y) for x, y in zip(a, b)]
    denom = math.fsum(float(value) ** 2 for value in b)
    return {
        "bitwise_equal": left == right,
        "different_values": sum(x != y for x, y in zip(a, b)),
        "max_abs_diff": max(map(abs, delta), default=0.0),
        "relative_l2": math.sqrt(math.fsum(value * value for value in delta) / denom) if denom else None,
        "left_sha256": hashlib.sha256(left).hexdigest(),
        "right_sha256": hashlib.sha256(right).hexdigest(),
    }


def main():
    result = {
        "scope": "verifier MoE input activations at absolute position 511; three requests per service arm",
        "model_identity": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "arms": {},
    }
    for arm in ("adaptive-cap8", "delayed-control"):
        requests = read_arm(ROOT / arm / "result" / "verify-moe-input.bin")
        transitions = {}
        for left, right, name in ((0, 1, "initial_to_intermediate"),
                                  (1, 2, "intermediate_to_recovery"),
                                  (0, 2, "initial_to_recovery")):
            layers = {}
            for layer in range(LAYERS):
                if requests[left][layer] != requests[right][layer]:
                    layers[str(layer)] = compare(requests[left][layer], requests[right][layer])
            transitions[name] = {
                "different_layer_count": len(layers),
                "first_different_layer": min(map(int, layers), default=None),
                "layers": layers,
            }
        result["arms"][arm] = {
            "records": 3 * LAYERS,
            "request_token_id": 271,
            "transitions": transitions,
        }
    out = ROOT / "verifier-input-analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({arm: {key: value["different_layer_count"]
                            for key, value in data["transitions"].items()}
                      for arm, data in result["arms"].items()}, indent=2))


if __name__ == "__main__":
    main()
