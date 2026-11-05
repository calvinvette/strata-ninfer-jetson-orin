#!/usr/bin/env python3
"""Independent scalar IQ2_S byte decoder and real-GGUF comparison helper.

The canonical 1024-entry IQ2_S grid is read from the pinned ggml-common.h;
block traversal, scale/sign handling and value placement below are a separate
scalar implementation.  The optional real-payload mode compares every decoded
expert value against GGML `to_float` dumps from native_expert_parity.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gguf_reader import GGUFFile

BLOCK_BYTES = 82
BLOCK_VALUES = 256
HIDDEN = 2560
INTERMEDIATE = 640
IQ4_NL_SYMBOLS = (-127, -104, -83, -65, -49, -35, -22, -10,
                  1, 13, 25, 38, 53, 69, 89, 113)


def load_grid(header: Path) -> tuple[int, ...]:
    text = header.read_text()
    match = re.search(r"GGML_TABLE_BEGIN\(uint64_t,\s*iq2s_grid,\s*1024\)(.*?)GGML_TABLE_END\(\)", text, re.S)
    if not match:
        # ggml-common.h uses a zero-argument end macro in some pinned revisions
        match = re.search(r"GGML_TABLE_BEGIN\(uint64_t,\s*iq2s_grid,\s*1024\)(.*?)GGML_TABLE_END", text, re.S)
    if not match:
        raise ValueError(f"cannot locate canonical iq2s_grid in {header}")
    values = tuple(int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", match.group(1)))
    if len(values) != 1024 or any(x >= 1 << 64 for x in values):
        raise ValueError(f"expected 1024 uint64 grid values, found {len(values)}")
    return values


def decode_block(block: bytes, grid: tuple[int, ...]) -> tuple[float, ...]:
    if len(block) != BLOCK_BYTES:
        raise ValueError("IQ2_S blocks are exactly 82 bytes")
    d = struct.unpack_from("<e", block, 0)[0]
    qs = block[2:66]
    qh = block[66:74]
    scales = block[74:82]
    out = [0.0] * BLOCK_VALUES
    for group32 in range(8):
        local_qh = qh[group32]
        local_scale = scales[group32]
        for subgroup8 in range(4):
            table_index = qs[4 * group32 + subgroup8] | ((local_qh << (8 - 2 * subgroup8)) & 0x300)
            pattern = grid[table_index]
            multiplier = d * (0.5 + ((local_scale >> (4 * (subgroup8 // 2))) & 0xF)) * 0.25
            signs = qs[32 + 4 * group32 + subgroup8]
            dst = 32 * group32 + 8 * subgroup8
            for lane in range(8):
                code = (pattern >> (8 * lane)) & 0xFF
                out[dst + lane] = multiplier * (-code if signs & (1 << lane) else code)
    return tuple(out)


def decode_row(payload: bytes, width: int, grid: tuple[int, ...]) -> tuple[float, ...]:
    if width % BLOCK_VALUES or len(payload) != width // BLOCK_VALUES * BLOCK_BYTES:
        raise ValueError("IQ2_S row has invalid width or byte length")
    values = []
    for offset in range(0, len(payload), BLOCK_BYTES):
        values.extend(decode_block(payload[offset:offset + BLOCK_BYTES], grid))
    return tuple(values)


def decode_iq4_nl_row(payload: bytes, width: int) -> tuple[float, ...]:
    if width % 32 or len(payload) != width // 32 * 18:
        raise ValueError("IQ4_NL row has invalid width or byte length")
    values = []
    for offset in range(0, len(payload), 18):
        d = struct.unpack_from("<e", payload, offset)[0]
        qs = payload[offset + 2:offset + 18]
        values.extend(d * IQ4_NL_SYMBOLS[qs[j] & 0xF] for j in range(16))
        values.extend(d * IQ4_NL_SYMBOLS[qs[j] >> 4] for j in range(16))
    return tuple(values)


def _half_bits(value: float) -> int:
    return struct.unpack("<H", struct.pack("<e", value))[0]


def self_test(grid: tuple[int, ...]) -> None:
    # All 10 index bits and each sign position are independently exercised;
    # scales cover zero, subnormal, unit, negative and finite extremes.
    cases = 0
    for table_index in range(1024):
        for lane in (0, 3, 7):
            block = bytearray(BLOCK_BYTES)
            block[:2] = struct.pack("<H", _half_bits(1.0))
            group, sub = 0, 0
            block[2 + 4 * group + sub] = table_index & 0xFF
            block[66 + group] = table_index >> 8
            block[74 + group] = 0x22
            block[2 + 32 + 4 * group + sub] = 1 << lane
            decoded = decode_block(bytes(block), grid)
            start = 32 * group + 8 * sub
            expected = grid[table_index]
            scale = (0.5 + 2) * 0.25
            for j in range(8):
                sign = -1 if j == lane else 1
                if decoded[start + j] != scale * ((expected >> (8 * j)) & 255) * sign:
                    raise AssertionError(f"grid/sign self-test failed at index={table_index}, lane={lane}, j={j}")
            cases += 1
    if cases != 3072:
        raise AssertionError("incomplete IQ2_S table self-test")


def compare_real(model_path: Path, layer: int, expert: int, reference_dir: Path,
                 grid: tuple[int, ...]) -> dict:
    gguf = GGUFFile(model_path)
    tensors = {}
    with model_path.open("rb") as f:
        for role, width, rows in (("gate", HIDDEN, INTERMEDIATE),
                                  ("up", HIDDEN, INTERMEDIATE),
                                  ("down", INTERMEDIATE, HIDDEN)):
            name = f"blk.{layer}.ffn_{role}_exps.weight"
            tensor = next((t for t in gguf.tensors if t.name == name), None)
            if tensor is None:
                raise ValueError(f"tensor {name} missing from shard; pass its owning GGUF shard")
            expected = "IQ2_S" if role != "down" else "IQ4_NL"
            if (tensor.type_name != expected or len(tensor.shape) != 3 or
                    tensor.shape[0] != width or tensor.shape[1] != rows):
                raise ValueError(f"unexpected tensor contract for {name}: {tensor.type_name} {tensor.shape}")
            if not 0 <= expert < tensor.shape[2]:
                raise ValueError(f"expert {expert} outside {name}")
            block_size = 82 if expected == "IQ2_S" else 18
            block_elems = 256 if expected == "IQ2_S" else 32
            row_bytes = width // block_elems * block_size
            f.seek(gguf.data_start + tensor.offset + expert * rows * row_bytes)
            raw = f.read(rows * row_bytes)
            if len(raw) != rows * row_bytes:
                raise IOError(f"short expert read for {name}")
            tensors[role] = (raw, rows, width, row_bytes)

    compared = 0
    max_abs = 0.0
    digest = hashlib.sha256()
    for role, (_, rows, width, row_bytes) in tensors.items():
        stem = f"layer-{layer}-expert-{expert}-{role}"
        reference = (reference_dir / f"{stem}.f32").read_bytes()
        if len(reference) != rows * width * 4:
            raise ValueError(f"reference has wrong size for {role}: {len(reference)}")
        raw = tensors[role][0]
        for row in range(rows):
            row_bytes_data = raw[row * row_bytes:(row + 1) * row_bytes]
            decoded = decode_row(row_bytes_data, width, grid) if role != "down" else decode_iq4_nl_row(row_bytes_data, width)
            encoded = struct.pack(f"<{width}f", *decoded)
            start = row * width * 4
            ref_row = reference[start:start + width * 4]
            if encoded != ref_row:
                # Report a useful numerical diagnostic on the first mismatch.
                actual = struct.unpack(f"<{width}f", encoded)
                expected = struct.unpack(f"<{width}f", ref_row)
                error = max(abs(a - b) for a, b in zip(actual, expected))
                raise AssertionError(f"{role} row {row} differs from GGML to_float; max_abs={error}")
            digest.update(encoded)
            compared += width
    return {"layer": layer, "expert": expert, "values_exact": compared,
            "max_abs_error": max_abs, "oracle_decoded_sha256": digest.hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ggml-common", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--model-shard", type=Path)
    parser.add_argument("--layer", type=int, default=2)
    parser.add_argument("--expert", type=int, default=174)
    parser.add_argument("--reference-dir", type=Path)
    args = parser.parse_args()
    grid = load_grid(args.ggml_common)
    if args.self_test:
        self_test(grid)
        print("IQ2_S scalar codec self-test: 3,072 table/sign combinations PASS")
    if args.model_shard:
        if not args.reference_dir:
            parser.error("--model-shard requires --reference-dir with GGML float dumps")
        result = compare_real(args.model_shard, args.layer, args.expert, args.reference_dir, grid)
        print(f"IQ2_S real expert decode exact: {result}")
    if not args.self_test and not args.model_shard:
        parser.error("select --self-test and/or --model-shard")


if __name__ == "__main__":
    main()
