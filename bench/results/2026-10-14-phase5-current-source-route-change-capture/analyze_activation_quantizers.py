#!/usr/bin/env python3
"""Compare source-defined CPU Q8_K and CUDA Q8_1 activation images for captured rows.

Uses only Python's standard library. This is a transcription of the finite-value
quantizer contracts, not a replacement for running the engine's native kernels.
"""
from __future__ import annotations

import pathlib
import statistics
import struct


ROOT = pathlib.Path(__file__).resolve().parent / "all-route-flips" / "inputs"
N = 2560


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def f16(x: float) -> float:
    return struct.unpack("<e", struct.pack("<e", x))[0]


def q8k(x: list[float]) -> list[float]:
    """ggml quantize_row_q8_K_ref: 256-wide, signed-maximum scale, nearest_int."""
    result: list[float] = []
    for start in range(0, len(x), 256):
        block = x[start : start + 256]
        maximum = max(block, key=abs)  # first maximum wins ties, as ggml's strict > scan
        if maximum == 0.0:
            result.extend([0.0] * len(block))
            continue
        inverse_scale = f32(-127.0 / maximum)
        scale = f32(1.0 / inverse_scale)
        for value in block:
            product = f32(inverse_scale * value)
            rounded_bits = struct.unpack("<I", struct.pack("<f", f32(product + 12582912.0)))[0]
            quant = (rounded_bits & 0x7FFFFF) - 0x400000
            result.append(f32(max(-128, min(127, quant)) * scale))
    return result


def q8_1(x: list[float]) -> list[float]:
    """CUDA q8_1_store: 32-wide absmax scale, roundf and fp16-stored scale."""
    result: list[float] = []
    for start in range(0, len(x), 32):
        block = x[start : start + 32]
        amax = max(map(abs, block))
        scale = f32(amax / 127.0)
        stored_scale = f32(f16(scale))
        for value in block:
            quotient = f32(value / scale) if amax != 0.0 else 0.0
            quant = 0 if amax == 0.0 else int(abs(quotient) + 0.5) * (1 if value >= 0 else -1)
            result.append(f32(max(-127, min(127, quant)) * stored_scale))
    return result


def rel_l1(a: list[float], b: list[float]) -> float:
    denom = sum(map(abs, b))
    return sum(abs(x - y) for x, y in zip(a, b)) / denom


def main() -> None:
    rows = []
    paths = sorted(ROOT.glob("layer0-row*.f32"))
    if len(paths) != 7:
        raise SystemExit(f"expected seven captured activations in {ROOT}, found {len(paths)}")
    for path in paths:
        data = path.read_bytes()
        if len(data) != N * 4:
            raise SystemExit(f"{path}: expected {N * 4} bytes, got {len(data)}")
        x = list(struct.unpack(f"<{N}f", data))
        cpu, gpu = q8k(x), q8_1(x)
        row = (path.name, rel_l1(cpu, x), rel_l1(gpu, x), rel_l1(cpu, gpu), sum(a != b for a, b in zip(cpu, gpu)))
        rows.append(row)
        print(f"{row[0]} Q8_K_L1={row[1]*100:.5f}% Q8_1_L1={row[2]*100:.5f}% "
              f"mutual_L1={row[3]*100:.5f}% unequal={row[4]}/{N}")
    med = [statistics.median(row[i] for row in rows) * 100 for i in (1, 2, 3)]
    print(f"median relative L1: Q8_K={med[0]:.5f}% Q8_1={med[1]:.5f}% mutual={med[2]:.5f}%")


if __name__ == "__main__":
    main()
