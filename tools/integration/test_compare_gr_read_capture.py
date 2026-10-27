#!/usr/bin/env python3
"""Tests for fused GR-read capture parsing and comparison."""
from pathlib import Path
import struct
import tempfile
import unittest

from compare_gr_read_capture import HEADER, compare, read_capture


def write_capture(path: Path, mixed_value: float) -> None:
    # HC=2, N=2, HC_LR=1: xn[4], lo[1], rs[2], inj_out[2], mixed[2].
    header = HEADER.pack(b"STGRRD1\0", 1, 3, 17, 99, 0, 2, 2, 1)
    payload = struct.pack("<11f", *([1.0] * 9), 2.0, mixed_value)
    path.write_bytes(header + payload)


class CompareGrReadCaptureTests(unittest.TestCase):
    def test_compares_each_read_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.bin"
            b = Path(tmp) / "b.bin"
            write_capture(a, 3.0)
            write_capture(b, 3.5)
            result = compare(a, b)
            self.assertEqual(result["first_differing_field"], "mixed")
            self.assertEqual(result["fields"]["xn"]["different"], 0)
            self.assertEqual(result["fields"]["mixed"]["different"], 1)

    def test_rejects_truncated_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.bin"
            write_capture(path, 3.0)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "payload"):
                read_capture(path)


if __name__ == "__main__":
    unittest.main()
