#!/usr/bin/env python3
"""Tests for opt-in QSA stage capture parsing and comparison."""
import struct
import tempfile
import unittest
from pathlib import Path

from compare_qsa_capture import HEADER, metrics, read_capture


class QsaCaptureTests(unittest.TestCase):
    def test_reads_qsa_capture_layout(self):
        header = HEADER.pack(b'STQSAD1\0', 1, 3, 127, 2, 3, 1, 2, 2, 42, 0)
        floats = tuple(float(i) for i in range(20))
        ids = (17, 23)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'qsa.bin'
            payload = (struct.pack('<10f', *floats[:10]) + struct.pack('<2i', *ids) +
                       struct.pack('<8f', *floats[10:18]) + struct.pack('<2f', *floats[18:]))
            path.write_bytes(header + payload)
            meta, fields, selected = read_capture(path)
        self.assertEqual(meta['layer'], 3)
        self.assertEqual(meta['position'], 127)
        self.assertEqual(fields['qsa_input'], (0.0, 1.0))
        self.assertEqual(fields['query'], (2.0, 3.0, 4.0))
        self.assertEqual(selected, ids)
        self.assertEqual(fields['projected_output'], (16.0, 17.0))
        self.assertEqual(fields['moe_input'], (18.0, 19.0))

    def test_metrics_counts_differences(self):
        self.assertEqual(metrics((1.0, 2.0), (1.0, 2.0))['different'], 0)
        self.assertEqual(metrics((1.0, 2.0), (1.0, 3.0))['different'], 1)

    def test_rejects_truncated_payload(self):
        header = HEADER.pack(b'STQSAD1\0', 1, 3, 127, 2, 3, 1, 2, 2, 42, 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'qsa.bin'
            path.write_bytes(header + b'\0')
            with self.assertRaisesRegex(ValueError, 'payload size'):
                read_capture(path)


if __name__ == '__main__':
    unittest.main()
