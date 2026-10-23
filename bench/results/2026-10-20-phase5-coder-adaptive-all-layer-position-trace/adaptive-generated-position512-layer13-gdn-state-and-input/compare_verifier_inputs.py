#!/usr/bin/env python3
"""Compare CUDA-side verifier MoE input captures across the three requests."""
import hashlib
import argparse
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = struct.Struct("<8sIIIIQq8i")
LAYERS = 48
WIDTH = 2560
POSITION = 512
TOKEN = 760


def read_requests(path, request_count):
    raw = path.read_bytes()
    offset = 0
    records = []
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError(f"{path}: truncated record header")
        magic, version, layer, rows, reserved, width, pos0, *tokens = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if (magic != b"STMOINP1" or version != 1 or rows != 1 or reserved != 0 or
                width != WIDTH or pos0 != POSITION or tokens[0] != TOKEN or not 0 <= layer < LAYERS):
            raise ValueError(f"{path}: unexpected capture header for layer {layer}")
        size = WIDTH * 4
        if len(raw) - offset < size:
            raise ValueError(f"{path}: truncated payload for layer {layer}")
        payload = raw[offset:offset + size]
        offset += size
        values = struct.unpack(f"<{WIDTH}f", payload)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{path}: non-finite value in layer {layer}")
        records.append((layer, payload))
    if len(records) != request_count * LAYERS:
        raise ValueError(f"{path}: expected {request_count * LAYERS} records, got {len(records)}")
    requests = []
    for index in range(request_count):
        group = records[index * LAYERS:(index + 1) * LAYERS]
        if [layer for layer, _ in group] != list(range(LAYERS)):
            raise ValueError(f"{path}: request {index} has missing or reordered layers")
        requests.append({layer: payload for layer, payload in group})
    return requests


def summarize(a, b):
    av = struct.unpack(f"<{WIDTH}f", a)
    bv = struct.unpack(f"<{WIDTH}f", b)
    delta = [float(x) - float(y) for x, y in zip(av, bv)]
    denom = math.fsum(float(x) ** 2 for x in bv)
    return {
        "bitwise_equal": a == b,
        "different_values": sum(x != y for x, y in zip(av, bv)),
        "max_abs_diff": max(map(abs, delta), default=0.0),
        "relative_l2": math.sqrt(math.fsum(x * x for x in delta) / denom) if denom else None,
        "left_sha256": hashlib.sha256(a).hexdigest(),
        "right_sha256": hashlib.sha256(b).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=ROOT,
                        help="paired campaign directory containing both arms")
    args = parser.parse_args()
    campaign = json.loads((args.run_dir / "campaign.json").read_text())
    if campaign.get("status") != "pass":
        raise ValueError("paired campaign did not pass")
    requests_meta = campaign["runs"][0]["analysis"]["requests"]
    request_names = [row["name"] for row in requests_meta]
    request_count = len(request_names)
    output = {
        "scope": "CUDA-side verifier MoE inputs at generated position 512",
        "width": WIDTH,
        "model_identity": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "requests": request_names,
        "arms": {},
    }
    for arm in ("adaptive-cap8", "delayed-control"):
        requests = read_requests(args.run_dir / arm / "result" / "verify-moe-input.bin", request_count)
        transitions = {}
        pairs = [(index, index + 1, f"{request_names[index]}_to_{request_names[index + 1]}")
                 for index in range(request_count - 1)]
        pairs.append((0, 2, f"{request_names[0]}_to_{request_names[2]}"))
        for left, right, name in pairs:
            layers = {
                str(layer): summarize(requests[left][layer], requests[right][layer])
                for layer in range(LAYERS)
                if requests[left][layer] != requests[right][layer]
            }
            transitions[name] = {
                "different_layer_count": len(layers),
                "first_different_layer": min(map(int, layers), default=None),
                "layers": layers,
            }
        output["arms"][arm] = {"record_count": request_count * LAYERS, "transitions": transitions}
    target = args.run_dir / "verifier-input-analysis.json"
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({arm: {
        name: {"count": data["different_layer_count"], "first": data["first_different_layer"]}
        for name, data in rows["transitions"].items()
    } for arm, rows in output["arms"].items()}, indent=2))


if __name__ == "__main__":
    main()
