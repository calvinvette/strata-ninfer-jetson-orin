#!/usr/bin/env python3
"""Compare exact prompt-end GDN bytes in the supervised three-arm campaign."""
import hashlib
import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation/prefill-gdn-exact-three-arm-checked"
ARMS = ("cpu_default", "cpu_mirror", "gpu_layer1")
PAIRS = (("cpu_default", "cpu_mirror"), ("cpu_mirror", "gpu_layer1"))
HEADER = struct.Struct("<8sQQ")


def read_dump(arm):
    path = CAMPAIGN / arm / "result/prefill-gdn.bin"
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise ValueError(f"{arm}: truncated GDN dump")
    magic, layers, floats_per_layer = HEADER.unpack_from(raw)
    if magic != b"STPFGDN1":
        raise ValueError(f"{arm}: unexpected GDN dump magic {magic!r}")
    layer_bytes = floats_per_layer * 4
    if layers != 36 or len(raw) != HEADER.size + layers * layer_bytes:
        raise ValueError(f"{arm}: invalid GDN dump dimensions or byte count")
    payload = raw[HEADER.size:]
    layer_sha256 = [hashlib.sha256(payload[i * layer_bytes:(i + 1) * layer_bytes]).hexdigest()
                    for i in range(layers)]
    return {
        "raw_dump_path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "layers": layers,
        "floats_per_layer": floats_per_layer,
        "payload_bytes": len(payload),
        "gdn_state_sha256_by_ordinal": layer_sha256,
        "payload": payload,
        "layer_bytes": layer_bytes,
    }


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN,
                    help="campaign directory containing the three arm subdirectories")
args = parser.parse_args()
CAMPAIGN = args.campaign.resolve()
dumps = {arm: read_dump(arm) for arm in ARMS}
result = {"schema": 1, "campaign": str(CAMPAIGN.relative_to(ROOT)),
          "raw_dump_retention": "The raw state files are compared directly, then removed from the tracked report; overall and per-slice SHA256 values are retained.",
          "arms": {}, "pairs": {}}
for arm, dump in dumps.items():
    result["arms"][arm] = {key: value for key, value in dump.items()
                           if key != "payload" and key != "layer_bytes"}
for left, right in PAIRS:
    a, b = dumps[left], dumps[right]
    layer_diffs = []
    for layer in range(a["layers"]):
        start = layer * a["layer_bytes"]
        end = start + a["layer_bytes"]
        first_byte = next((i for i, (x, y) in enumerate(zip(a["payload"][start:end], b["payload"][start:end]))
                           if x != y), None)
        if first_byte is not None:
            layer_diffs.append({
                "gdn_state_ordinal": layer,
                "first_differing_byte_in_layer": first_byte,
                "first_differing_float_word": first_byte // 4,
                "different_bytes_in_layer": sum(x != y for x, y in zip(a["payload"][start:end], b["payload"][start:end])),
            })
    result["pairs"][f"{left}_vs_{right}"] = {
        "exact_bytes_equal": a["payload"] == b["payload"],
        "first_differing_gdn_state_ordinal": layer_diffs[0]["gdn_state_ordinal"] if layer_diffs else None,
        "different_gdn_states": len(layer_diffs),
        "gdn_state_differences": layer_diffs,
    }

output = CAMPAIGN / "prefill-gdn-exact-analysis.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"output": str(output), "pairs": {
    pair: {key: value for key, value in data.items() if key != "gdn_state_differences"}
    for pair, data in result["pairs"].items()}}, indent=2))
