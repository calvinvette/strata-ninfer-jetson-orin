#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from array import array

from compare_qsa_kv_capture import HEADER, compare


def write_capture(path, key, value, valid_count=2):
    capacity = len(key)
    n_kv = len(key[0])
    head_dim = len(key[0][0])
    header = HEADER.pack(b"STQKVD1", 1, 3, 125, n_kv, head_dim, capacity, 271, valid_count)
    payload = array("f", [v for rows in (key, value) for row in rows for head in row for v in head])
    path.write_bytes(header + payload.tobytes())


class CompareQsaKvCaptureTests(unittest.TestCase):
    def test_compares_valid_cells_and_ignores_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = [[[float(cell * 4 + d) for d in range(4)]] for cell in range(3)]
            value = [[[float(cell * 4 + d + 20) for d in range(4)]] for cell in range(3)]
            other_key, other_value = [[x[:] for x in cell] for cell in key], [[x[:] for x in cell] for cell in value]
            other_key[2][0] = [x + 1000 for x in other_key[2][0]]
            other_value[2][0] = [x - 1000 for x in other_value[2][0]]
            write_capture(root / "ref", key, value)
            write_capture(root / "cand", other_key, other_value)
            result = compare(root / "ref", root / "cand")
            self.assertEqual(result["key"]["different"], 0)
            self.assertEqual(result["value"]["different"], 0)
            self.assertEqual(result["valid_count"], 2)

    def test_detects_valid_cache_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = [[[1.0] * 4] for _ in range(2)]
            value = [[[2.0] * 4] for _ in range(2)]
            other = [[x[:] for x in cell] for cell in key]
            other[1][0][2] += 0.25
            write_capture(root / "ref", key, value, 2)
            write_capture(root / "cand", other, value, 2)
            self.assertEqual(compare(root / "ref", root / "cand")["key"]["different"], 1)


if __name__ == "__main__":
    unittest.main()
