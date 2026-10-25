#!/usr/bin/env python3
"""Scalar Q2_0 expert reference for local Flash-Next GGUF weights and F32 activations."""

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gguf_reader import GGUFFile


def half_to_float(bits):
    return struct.unpack("<e", struct.pack("<H", bits))[0]


def decode_block(block):
    if len(block) != 18:
        raise ValueError("Q2_0 block must be 18 bytes")
    scale = half_to_float(struct.unpack_from("<H", block)[0])
    codes = block[2:]
    return [scale * (((codes[j // 4] >> ((j % 4) * 2)) & 3) - 1) for j in range(64)]


def decode_row(blob, width):
    if width % 64 or len(blob) != width // 64 * 18:
        raise ValueError("row width/blob size violates Q2_0 block geometry")
    values = []
    for off in range(0, len(blob), 18):
        values.extend(decode_block(blob[off : off + 18]))
    return values


def dot(row, vector):
    return sum(float(w) * float(x) for w, x in zip(row, vector))


def read_rows(gguf_path, gguf, name, expert, rows, width):
    tensor = next(t for t in gguf.tensors if t.name == name)
    if tensor.type_name != "Q2_0" or tensor.shape != [width, rows, 512]:
        raise ValueError(f"unexpected tensor contract: {name} {tensor.type_name} {tensor.shape}")
    if expert < 0 or expert >= tensor.shape[2]:
        raise ValueError("expert id outside tensor")
    row_bytes = width // 64 * 18
    with gguf_path.open("rb") as source:
        source.seek(gguf.data_start + tensor.offset + expert * rows * row_bytes)
        payload = source.read(rows * row_bytes)
    if len(payload) != rows * row_bytes:
        raise IOError(f"short read for {name}")
    return (decode_row(payload[i * row_bytes : (i + 1) * row_bytes], width) for i in range(rows))


def run(gguf_path, activation_path, layer, expert, output_f64=None):
    gguf_path = Path(gguf_path).expanduser()
    activation_path = Path(activation_path).expanduser()
    gguf = GGUFFile(gguf_path)
    activation_bytes = activation_path.read_bytes()
    hidden, intermediate = 2560, 640
    if len(activation_bytes) != hidden * 4:
        raise ValueError(f"activation must contain exactly {hidden} F32 values")
    x = struct.unpack(f"<{hidden}f", activation_bytes)
    prefix = f"blk.{layer}."
    gate = [dot(row, x) for row in read_rows(gguf_path, gguf, prefix + "ffn_gate_exps.weight", expert,
                                              intermediate, hidden)]
    up = [dot(row, x) for row in read_rows(gguf_path, gguf, prefix + "ffn_up_exps.weight", expert,
                                            intermediate, hidden)]
    hidden_values = []
    for g, u in zip(gate, up):
        sigmoid = 1.0 / (1.0 + math.exp(-g)) if g >= 0 else math.exp(g) / (1.0 + math.exp(g))
        hidden_values.append(g * sigmoid * u)
    output = [dot(row, hidden_values) for row in read_rows(gguf_path, gguf, prefix + "ffn_down_exps.weight",
                                                           expert, hidden, intermediate)]
    packed_output = struct.pack(f"<{hidden}d", *output)
    if output_f64 is not None:
        Path(output_f64).expanduser().write_bytes(packed_output)
    return {
        "schema": "strata-q2-expert-oracle-v1",
        "gguf": str(gguf_path),
        "gguf_size_bytes": gguf_path.stat().st_size,
        "activation": str(activation_path),
        "activation_sha256": hashlib.sha256(activation_bytes).hexdigest(),
        "activation_provenance": "caller-supplied F32 vector; provenance must be stated by the caller",
        "layer": layer,
        "expert": expert,
        "geometry": {"hidden": hidden, "intermediate": intermediate, "routed_experts": 512},
        "arithmetic": "Q2_0 decoded to FP64; FP64 dot sums and SiLU; unweighted routed output",
        "output_sha256_f64le": hashlib.sha256(packed_output).hexdigest(),
        "output_max_abs": max(abs(v) for v in output),
        "output_rms": math.sqrt(sum(v * v for v in output) / hidden),
        "gate_max_abs": max(abs(v) for v in gate),
        "up_max_abs": max(abs(v) for v in up),
        "hidden_max_abs": max(abs(v) for v in hidden_values),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gguf", type=Path)
    parser.add_argument("activation_f32", type=Path)
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--expert", type=int, required=True)
    parser.add_argument("--output-f64", type=Path, help="optional path for the little-endian FP64 output row")
    args = parser.parse_args()
    print(json.dumps(run(args.gguf, args.activation_f32, args.layer, args.expert, args.output_f64), indent=2))


if __name__ == "__main__":
    main()
