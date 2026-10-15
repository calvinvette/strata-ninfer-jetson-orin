#!/usr/bin/env python3
"""Check that a local Strata native expert pack matches a Coder GGUF source."""
import argparse
import hashlib
import json
import pathlib
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", required=True, type=pathlib.Path, help="Coder IQ1_M shard 1")
    ap.add_argument("--pack", required=True, type=pathlib.Path, help="existing Strata pack")
    args = ap.parse_args()
    repo = pathlib.Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo / "tools"))
    import iq_pack  # noqa: E402 - use the same source parser/contract as the pack builder

    model = iq_pack.Model(args.gguf)
    layout = iq_pack.expert_layout(model, args.gguf)
    if isinstance(layout, str):
        raise SystemExit(f"model expert layout refused: {layout}")
    layers, text, n_experts, arena_bytes = layout
    actual_map = (args.pack / "native_experts.txt").read_text(encoding="utf-8")
    expected_source = iq_pack.experts_source(model, text, arena_bytes)
    actual_source = json.loads((args.pack / "experts.bin.src.json").read_text(encoding="utf-8"))
    sampled = []
    expert_path = args.pack / "experts.bin"
    with expert_path.open("rb") as f:
        for layer, _gt, _dt, offset, blob_bytes, tensors in (layers[0], layers[len(layers) // 2], layers[-1]):
            for expert in (0, n_experts - 1):
                f.seek(offset + expert * blob_bytes)
                expected = b"".join(model.bytes(t.name).reshape(n_experts, -1)[expert].tobytes()
                                    for t in tensors)
                got = f.read(blob_bytes)
                sampled.append({"layer": layer, "expert": expert, "matches": got == expected,
                                "blob_bytes": blob_bytes})
    result = {
        "gguf_shards": [{"name": p.name, "size_bytes": p.stat().st_size} for p in model.paths],
        "layers": len(layers), "experts_per_layer": n_experts, "expert_arena_bytes": arena_bytes,
        "generated_native_experts_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "pack_native_experts_sha256": hashlib.sha256(actual_map.encode()).hexdigest(),
        "expert_layout_matches": actual_map == text,
        "sidecar_matches": actual_source == expected_source,
        "sampled_expert_blobs": sampled,
        "pass": actual_map == text and actual_source == expected_source and all(x["matches"] for x in sampled),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
