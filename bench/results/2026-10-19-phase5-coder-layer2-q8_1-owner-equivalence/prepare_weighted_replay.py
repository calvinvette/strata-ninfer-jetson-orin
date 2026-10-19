#!/usr/bin/env python3
"""Extract a matched layer-2 service row for independent CPU/CUDA expert replay."""
import gzip
import hashlib
import json
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "weighted-replay-retry1"
HEADER = struct.Struct("<8sIiiqQQQQQ8i")
TARGETS = (174, 62, 69, 130, 143, 151, 28)
ARMS = ("cpu_mirror", "gpu_layer2")
POSITION = 511
TOKEN_ID = 271


def read_jsonl(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as stream:
        values = [json.loads(line) for line in stream]
    return values[0], values[1:]


def artifact(arm, key):
    req_path = HERE / "device-route-pair-retry1" / arm / "run" / "requests.json"
    req = json.loads(req_path.read_text())
    item = req["capture_artifacts"][key]
    path = HERE / item["path"]
    data = gzip.open(path, "rb").read() if str(path).endswith(".gz") else path.read_bytes()
    if hashlib.sha256(data).hexdigest() != item["sha256"] or len(data) != item["bytes"]:
        raise ValueError(f"{arm}/{key}: capture checksum mismatch")
    return req, data


def read_layer_row(data, expected_layer, position):
    offset = 0
    found = {}
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError("truncated STGDIAG4 header")
        magic, version, layer, count, pos0, n, c, hv, zv, state_n, *tokens = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if magic != b"STGDIAG4" or version != 4 or layer != expected_layer or n != 2560:
            raise ValueError("unexpected verifier layer diagnostic header")
        payload = count * (4 * n + 2 * c + 2 * hv + 2 * zv) * 4
        if offset + payload > len(data):
            raise ValueError("truncated verifier layer diagnostic payload")
        x_at = offset + (2 * count * n + 2 * count * c + 2 * count * hv + 2 * count * zv) * 4
        y_at = x_at + count * n * 4
        for index in range(count):
            found[pos0 + index] = {
                "token_id": tokens[index],
                "ffn_x": struct.unpack_from(f"<{n}f", data, x_at + index * n * 4),
                "ffn_y": struct.unpack_from(f"<{n}f", data, y_at + index * n * 4),
            }
        offset += payload
    if position not in found:
        raise ValueError(f"position {position} absent from verifier capture")
    return found[position]


def write_f32(path, values):
    path.write_bytes(struct.pack(f"<{len(values)}f", *values))


def main():
    OUT.mkdir(exist_ok=False)
    arms = {}
    for arm in ARMS:
        req, diag_data = artifact(arm, "combined_moe")
        row = read_layer_row(diag_data, 2, POSITION)
        if row["token_id"] != TOKEN_ID:
            raise ValueError(f"{arm}: unexpected position {POSITION} token {row['token_id']}")
        route_req, route_data = artifact(arm, "device_moe_routes_layer2")
        route_lines = route_data.decode().splitlines()
        route_header = json.loads(route_lines[0])
        route_rows = [json.loads(line) for line in route_lines[1:]]
        route = next((item for item in route_rows if item["position"] == POSITION), None)
        if route_header != {"format": "strata-verify-moe-route-v1", "k": 10} or route is None:
            raise ValueError(f"{arm}: invalid device route capture")
        host_req, host_data = artifact(arm, "routes_all_layers")
        host_header, host_rows = read_jsonl_bytes(host_data)
        host = next((item for item in host_rows if item["layer"] == 2 and item["position"] == POSITION), None)
        if host is None or host["token_id"] != TOKEN_ID:
            raise ValueError(f"{arm}: missing keyed host layer-2 route")
        if host["ids"] != route["ids"]:
            raise ValueError(f"{arm}: host and device route IDs differ")
        # The JSONL host trace prints rounded decimal activations. The binary
        # verifier diagnostic remains the exact input used below.
        host_input_delta = max(abs(a - b) for a, b in zip(host["activation"], row["ffn_x"]))
        if host_input_delta > 1e-7:
            raise ValueError(f"{arm}: host route is not near the exact device input ({host_input_delta})")
        if host["dispatch"] < 0:
            raise ValueError(f"{arm}: invalid dispatch identifier")
        owners = {expert: owner for expert, owner in zip(host["ids"], host["route_kind"])}
        outputs_req = json.loads((HERE / "device-route-pair-retry1" / arm / "run" / "requests.json").read_text())
        _, cpu_output_data = artifact(arm, "cpu_outputs_layer2")
        output_header, output_rows = read_jsonl_bytes(cpu_output_data)
        if output_header != {"format": "strata-moe-cpu-output-v2", "n_embd": 2560}:
            raise ValueError(f"{arm}: unsupported CPU output capture")
        cpu_outputs = {item["expert"]: item for item in output_rows
                       if item["position"] == POSITION and item["token_id"] == TOKEN_ID}
        sup = json.loads((HERE / "device-route-pair-retry1" / arm / "supervisor" / "result.json").read_text())
        if sup["status"] != "pass" or sup["returncode"] != 0:
            raise ValueError(f"{arm}: service supervisor failed")
        arms[arm] = {"request": req, "row": row, "route": route, "host": host,
                     "owners": owners, "cpu_outputs": cpu_outputs, "supervisor": sup,
                     "host_input_max_abs_delta": host_input_delta}

    left, right = (arms[arm] for arm in ARMS)
    if left["request"]["prompt_sha256"] != right["request"]["prompt_sha256"]:
        raise ValueError("prompt identity differs")
    if left["row"]["ffn_x"] != right["row"]["ffn_x"]:
        raise ValueError("device layer-2 inputs differ")
    if left["route"]["ids"] != right["route"]["ids"] or left["route"]["weights"] != right["route"]["weights"]:
        raise ValueError("device layer-2 routes/weights differ")
    for expert in TARGETS:
        if left["owners"].get(expert) != -1 or right["owners"].get(expert) != 0:
            raise ValueError(f"target expert {expert} did not change CPU->GPU owner")
        if expert not in left["cpu_outputs"]:
            raise ValueError(f"missing CPU mirror output for target expert {expert}")
        item = left["cpu_outputs"][expert]
        if item["dispatch"] != left["host"]["dispatch"] or len(item["output"]) != 2560:
            raise ValueError(f"target expert {expert} CPU result has wrong dispatch/width")
        target = OUT / f"service-cpu-expert-{expert}.f32"
        write_f32(target, item["output"])

    write_f32(OUT / "activation-position-511.f32", left["row"]["ffn_x"])
    write_f32(OUT / "combined-ffn-y-cpu-mirror.f32", left["row"]["ffn_y"])
    write_f32(OUT / "combined-ffn-y-gpu-layer2.f32", right["row"]["ffn_y"])
    evidence = {
        "position": POSITION, "token_id": TOKEN_ID, "layer": 2,
        "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
        "quantization": "IQ1_M", "tensor_pair": "IQ2_S/IQ4_NL",
        "selector": "iq2_s/iq4_nl@layer=2", "experts_moved_cpu_to_gpu": list(TARGETS),
        "device_input_bitwise_equal": True, "device_topk_ids_equal": True,
        "device_router_weights_equal": True,
        "host_route_text_max_abs_delta_from_device_input": {
            arm: arms[arm]["host_input_max_abs_delta"] for arm in ARMS
        },
        "ids": left["route"]["ids"], "weights": left["route"]["weights"],
        "owners_cpu_mirror": left["host"]["route_kind"],
        "owners_gpu_layer2": right["host"]["route_kind"],
        "prompt_sha256": left["request"]["prompt_sha256"],
        "completion_ids_equal": left["request"]["completion_ids"] == right["request"]["completion_ids"],
        "inputs_sha256": hashlib.sha256((OUT / "activation-position-511.f32").read_bytes()).hexdigest(),
        "source_capture_binary_sha256": left["request"].get("binary_sha256"),
        "source_capture": "device-route-pair-retry1; original service binary/source identity in parent analysis.json",
    }
    (OUT / "row.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


def read_jsonl_bytes(data):
    lines = data.decode().splitlines()
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:]]


if __name__ == "__main__":
    main()
