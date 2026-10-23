#!/usr/bin/env python3
"""Compare repeated layer-27 dispatch and verifier outputs against same-input oracles."""
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIDTH = 2560
LAYER = 27
POSITION = 511

spec = importlib.util.spec_from_file_location(
    "parts_compare", ROOT.parent / "compare_layer25_verifier_parts.py")
parts_compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parts_compare)
INPUT_HEADER = struct.Struct("<8sIIIIQq8i")


def load_dispatch(path):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if not records or records[0].get("format") != "strata-moe-dispatch-v3":
        raise ValueError(f"invalid dispatch capture: {path}")
    return [row for row in records[1:]
            if row["layer"] == LAYER and row["position"] == POSITION]


def load_verifier_inputs(path):
    raw = path.read_bytes()
    offset = 0
    values = []
    while offset < len(raw):
        magic, version, layer, rows, reserved, width, position, *tokens = INPUT_HEADER.unpack_from(raw, offset)
        offset += INPUT_HEADER.size
        if magic != b"STMOINP1" or version != 1 or layer != LAYER or rows != 1 or \
                reserved != 0 or width != WIDTH or position != POSITION:
            raise ValueError(f"invalid verifier input record in {path}")
        size = WIDTH * 4
        values.append(raw[offset:offset + size])
        offset += size
    if offset != len(raw) or len(values) != 3:
        raise ValueError(f"expected three verifier inputs in {path}, got {len(values)}")
    return values


def main():
    oracle = ROOT / "oracle-current"
    oracle_rows = {}
    for kind in ("cpu", "gpu"):
        raw = (oracle / f"layer-27-expert-175-{kind}-output.f32").read_bytes()
        if len(raw) != WIDTH * 4:
            raise ValueError(f"invalid {kind} oracle output size")
        oracle_rows[kind] = struct.unpack(f"<{WIDTH}f", raw)

    result = {
        "scope": "three repeated 512-token prompt requests, layer 27, position 511",
        "model": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
        "layer": LAYER,
        "position": POSITION,
        "owner_encoding": {"negative": "CPU", "non-negative": "CUDA"},
        "oracle_activation_sha256": hashlib.sha256(
            (oracle / "layer27-expert175-activation.f32").read_bytes()).hexdigest(),
        "arms": {},
    }
    for arm in ("delayed-control", "adaptive-cap8"):
        run = ROOT / arm / "result"
        dispatch = load_dispatch(run / "all-layer-position511.jsonl")
        verifier_inputs = load_verifier_inputs(run / "verify-moe-input.bin")
        routes = [json.loads(line) for line in
                  (run / "verify-moe-routes.jsonl").read_text().splitlines()][1:]
        routes = [row for row in routes
                  if row.get("layer") == LAYER and row.get("position") == POSITION]
        _, parts = parts_compare.read_parts(run / "verify-moe-parts.bin", LAYER, {POSITION})
        _, outputs = parts_compare.read_outputs(run / "verify-moe-output.bin", LAYER, {POSITION})
        if not (len(dispatch) == 2 and len(routes) == len(parts) == len(outputs) == 3):
            raise ValueError(f"{arm}: expected three matching route/output rows")
        index = routes[0]["ids"].index(175)
        requests = []
        for i, (route, part, output) in enumerate(zip(routes, parts, outputs)):
            endpoint_dispatch = dispatch[0] if i == 0 else (dispatch[-1] if i == 2 else None)
            if endpoint_dispatch is not None and (endpoint_dispatch["ids"] != route["ids"] or
                                                   endpoint_dispatch["token_id"] != route["token_id"]):
                raise ValueError(f"{arm} request {i}: dispatch/verifier route mismatch")
            row = part["parts"][index * WIDTH:(index + 1) * WIDTH]
            oracle_matches = [kind for kind in ("cpu", "gpu")
                              if parts_compare.summarize(oracle_rows[kind], row)["different_values"] == 0]
            owner = ("CPU" if oracle_matches == ["cpu"] else
                     "CUDA" if oracle_matches == ["gpu"] else "ambiguous")
            if endpoint_dispatch is not None:
                captured_owner = "CPU" if endpoint_dispatch["route_kind"][index] < 0 else "CUDA"
                if captured_owner != owner:
                    raise ValueError(f"{arm} request {i}: route owner disagrees with same-input oracle")
            requests.append({
                "index": i,
                "token_id": route["token_id"],
                "owner": owner,
                "route_kind": endpoint_dispatch["route_kind"][index] if endpoint_dispatch else None,
                "route_owner_capture": endpoint_dispatch is not None,
                "expert_ids_identical_to_first": route["ids"] == routes[0]["ids"],
                "router_weights_identical_to_first": route["weights"] == routes[0]["weights"],
                "dispatch_input_identical_to_first": (
                    endpoint_dispatch["activation"] == dispatch[0]["activation"]
                    if endpoint_dispatch is not None else None),
                "verifier_input_bit_identical_to_first": verifier_inputs[i] == verifier_inputs[0],
                "expert_row_matches_oracle": oracle_matches,
                "expert_row_vs_cpu_oracle": parts_compare.summarize(oracle_rows["cpu"], row),
                "expert_row_vs_gpu_oracle": parts_compare.summarize(oracle_rows["gpu"], row),
                "shared_output_vs_first": parts_compare.summarize(outputs[0]["shared"], output["shared"]),
                "combined_output_vs_first": parts_compare.summarize(outputs[0]["combined"], output["combined"]),
            })
        result["arms"][arm] = {
            "binary_sha256": json.loads((run / "analysis.json").read_text())["binary_sha256"],
            "requests": requests,
            "dispatch_sha256": hashlib.sha256(
                (run / "all-layer-position511.jsonl").read_bytes()).hexdigest(),
            "parts_sha256": hashlib.sha256((run / "verify-moe-parts.bin").read_bytes()).hexdigest(),
            "outputs_sha256": hashlib.sha256((run / "verify-moe-output.bin").read_bytes()).hexdigest(),
        }
    out = ROOT / "layer27-analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({arm: [
        {"index": row["index"], "owner": row["owner"],
         "expert_oracle": row["expert_row_matches_oracle"],
         "combined_diff_values": row["combined_output_vs_first"]["different_values"]}
        for row in data["requests"]]
        for arm, data in result["arms"].items()}, indent=2))


if __name__ == "__main__":
    main()
