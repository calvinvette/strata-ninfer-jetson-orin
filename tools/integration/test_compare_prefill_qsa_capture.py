#!/usr/bin/env python3
"""Synthetic coverage for the prompt-prefill QSA capture reader."""
from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from compare_prefill_qsa_capture import HEADER, compare, read_capture


def write_capture(path: Path, *, position: int = 123, token: int = 271,
                  query_delta: float = 0.0) -> None:
    n, q, idx, kv, cap = 2, 2, 1, 1, 2
    header = HEADER.pack(b'STQPFD1\0', 1, 3, position, n, q, idx, kv, cap, token, 0)
    arrays = [
        (1.0, 2.0),                 # input
        (1.0 + query_delta, 2.0),   # query
        (3.0,),                     # index query
        (4.0,),                     # current key
        (5.0,),                     # current value
    ]
    payload = bytearray(header)
    for values in arrays:
        payload.extend(struct.pack(f'<{len(values)}f', *values))
    payload.extend(struct.pack('<2i', 0, 1))
    payload.extend(struct.pack('<2f', 6.0, 7.0))  # attention
    payload.extend(struct.pack('<2H', 0x3c00, 0x4000))  # gated fp16: 1, 2
    payload.extend(struct.pack('<2f', 8.0, 9.0))  # projection
    path.write_bytes(payload)


class PrefillQsaCaptureTest(unittest.TestCase):
    def test_compare_reports_target_and_field_difference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / 'a.qsa', root / 'b.qsa'
            write_capture(a)
            write_capture(b, query_delta=0.25)
            result = compare(a, b)
            self.assertTrue(result['selection_equal'])
            self.assertEqual((result['header']['layer'], result['header']['position']), (3, 123))
            self.assertEqual(result['fields']['query']['different'], 1)
            self.assertEqual(result['fields']['gated_attention_f16']['different'], 0)

    def test_rejects_truncated_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.qsa'
            write_capture(path)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'payload size'):
                read_capture(path)

    def test_rejects_different_target_positions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / 'a.qsa', root / 'b.qsa'
            write_capture(a)
            write_capture(b, position=124)
            with self.assertRaisesRegex(ValueError, 'headers differ'):
                compare(a, b)


if __name__ == '__main__':
    unittest.main()
