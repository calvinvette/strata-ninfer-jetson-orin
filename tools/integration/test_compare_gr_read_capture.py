#!/usr/bin/env python3
"""Tests for fused GR-read capture parsing and comparison."""
from pathlib import Path
import struct
import tempfile
import unittest

from compare_gr_read_capture import (GDN_V4_HEADER, GDN_V5_HEADER, HEADER, compare,
                                     read_capture)


def write_capture(path: Path, mixed_value: float) -> None:
    # HC=2, N=2, HC_LR=1: xn[4], lo[1], rs[2], inj_out[2], mixed[2].
    header = HEADER.pack(b"STGRRD1\0", 1, 3, 17, 99, 0, 2, 2, 1)
    payload = struct.pack("<11f", *([1.0] * 9), 2.0, mixed_value)
    previous = path.read_bytes() if path.exists() else b""
    path.write_bytes(previous + header + payload)


def write_capture_v2(path: Path, residual: tuple[float, float], mixed: tuple[float, float]) -> None:
    # R[2], xn[4], lo[1], rs[2], inj_out[2], mixed[2].
    header = HEADER.pack(b"STGRRD2\0", 2, 3, 17, 99, 0, 2, 2, 1)
    payload = struct.pack("<13f", *residual, *([1.0] * 9), *mixed)
    path.write_bytes(header + payload)


def write_gr(path: Path, mixed: tuple[float, float] = (2.0, 3.0), position: int = 17) -> None:
    header = HEADER.pack(b"STGRRD1\0", 1, 3, position, 99, 0, 2, 2, 1)
    payload = struct.pack("<11f", *([1.0] * 9), *mixed)
    path.write_bytes(header + payload)


def write_gdn(path: Path, magic: bytes, x: tuple[float, float], position: int = 17) -> None:
    tokens = (99, 0, 0, 0, 0, 0, 0, 0)
    if magic == b"STGDIAG4":
        header = GDN_V4_HEADER.pack(magic, 4, 3, 1, position, 2, 2, 1, 2, 5, *tokens)
    else:
        positions = (position, 0, 0, 0, 0, 0, 0, 0)
        slots = (-1, 0, 0, 0, 0, 0, 0, 0)
        header = GDN_V5_HEADER.pack(magic, 5, 3, 1, position, 2, 2, 1, 2, 5,
                                    *positions, *slots, *tokens)
    # n=2, conv=2, heads=1, value=2 => 18 float32 stage values.
    payload = struct.pack("<18f", *x, *([1.0] * 16))
    previous = path.read_bytes() if path.exists() else b""
    path.write_bytes(previous + header + payload)


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

    def test_links_same_run_gdn_x_to_fused_mixed_v4_and_v5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for version, magic in ((4, b"STGDIAG4"), (5, b"STGDIAG5")):
                strata_read = root / f"strata-{version}.gr"
                ninfer_read = root / f"ninfer-{version}.gr"
                strata_gdn = root / f"strata-{version}.gdn"
                ninfer_gdn = root / f"ninfer-{version}.gdn"
                write_gr(strata_read)
                write_gr(ninfer_read)
                write_gdn(strata_gdn, magic, (2.0, 3.0))
                write_gdn(ninfer_gdn, magic, (2.0, 4.0))
                result = compare(strata_read, ninfer_read, strata_gdn, ninfer_gdn)
                self.assertEqual(result["gdn_x_to_gr_mixed"]["strata"]["different"], 0)
                self.assertEqual(result["gdn_x_to_gr_mixed"]["ninfer"]["different"], 1)
                self.assertEqual(result["gdn_x_cross_backend"]["different"], 1)

    def test_compares_v2_residual_input_before_normalized_xn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a.v2", root / "b.v2"
            write_capture_v2(a, (1.0, 2.0), (4.0, 5.0))
            write_capture_v2(b, (1.0, 2.0), (4.0, 5.0))
            result = compare(a, b)
            self.assertEqual(result["header"]["version"], 2)
            self.assertEqual(result["fields"]["R"]["different"], 0)
            self.assertEqual(result["fields"]["xn"]["different"], 0)
            self.assertIsNone(result["first_differing_field"])

    def test_compares_multiple_gdn_positions_and_links_selected_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            strata_read, ninfer_read = root / "strata.gr", root / "ninfer.gr"
            strata_gdn, ninfer_gdn = root / "strata.gdn", root / "ninfer.gdn"
            write_gr(strata_read, position=18)
            write_gr(ninfer_read, position=18)
            for path, second in ((strata_gdn, 3.0), (ninfer_gdn, 4.0)):
                write_gdn(path, b"STGDIAG5", (2.0, 3.0), position=17)
                write_gdn(path, b"STGDIAG5", (2.0, second), position=18)
                write_gdn(path, b"STGDIAG5", (7.0, 8.0), position=19)
            result = compare(strata_read, ninfer_read, strata_gdn, ninfer_gdn)
            self.assertEqual(result["gdn_x_to_gr_mixed"]["strata"]["different"], 0)
            self.assertEqual(result["gdn_x_to_gr_mixed"]["ninfer"]["different"], 1)
            self.assertEqual([r["position"] for r in result["gdn_x_positions_compared"]], [17, 18, 19])
            self.assertEqual(result["first_differing_gdn_x_position"], 18)


if __name__ == "__main__":
    unittest.main()
