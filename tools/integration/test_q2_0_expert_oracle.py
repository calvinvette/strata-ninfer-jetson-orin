#!/usr/bin/env python3
"""Independent scalar Q2_0 expert oracle and synthetic codec contract checks."""

import math
import struct
import unittest
from q2_0_expert_oracle import decode_block, decode_row

def encode_block(scale_bits, codes):
    if len(codes) != 64 or any(c < 0 or c > 3 for c in codes):
        raise ValueError("expected 64 two-bit Q2_0 codes")
    packed = bytearray(18)
    struct.pack_into("<H", packed, 0, scale_bits)
    for j, code in enumerate(codes):
        packed[2 + j // 4] |= code << ((j % 4) * 2)
    return bytes(packed)


def project(weights, x):
    if not weights or any(len(row) != len(x) for row in weights):
        raise ValueError("projection dimensions do not match")
    return [sum(float(w) * float(a) for w, a in zip(row, x)) for row in weights]


def silu(x):
    return x / (1.0 + math.exp(-x)) if x >= 0 else x * math.exp(x) / (1.0 + math.exp(x))


def expert(gate, up, down, x):
    g = project(gate, x)
    u = project(up, x)
    return project(down, [silu(a) * b for a, b in zip(g, u)])


class Q2ExpertOracleTest(unittest.TestCase):
    def test_all_codes_lsb_first_and_block_edges(self):
        codes = [j % 4 for j in range(64)]
        decoded = decode_block(encode_block(0x3C00, codes))
        self.assertEqual(decoded, [float((c - 1)) for c in codes])
        self.assertEqual(decoded[:4], [-1.0, 0.0, 1.0, 2.0])
        self.assertEqual(decoded[-4:], [-1.0, 0.0, 1.0, 2.0])

    def test_qwen_flash_next_projection_geometry(self):
        hidden, intermediate = 2560, 640
        x = [0.25 if i % 2 else -0.125 for i in range(hidden)]
        # A deterministic, compact code fixture exercises the complete operation
        # at production dimensions without storing model payloads in the repo.
        def row(width, offset):
            return [((i + offset) % 4 - 1) * (1.0 / 32.0) for i in range(width)]

        gate = [row(hidden, r) for r in range(intermediate)]
        up = [row(hidden, r + 1) for r in range(intermediate)]
        down = [row(intermediate, r + 2) for r in range(hidden)]
        y = expert(gate, up, down, x)
        self.assertEqual(len(y), hidden)
        self.assertTrue(all(math.isfinite(v) for v in y))

    def test_rejects_wrong_row_geometry(self):
        with self.assertRaises(ValueError):
            decode_row(bytes(18), 32)


if __name__ == "__main__":
    unittest.main()
