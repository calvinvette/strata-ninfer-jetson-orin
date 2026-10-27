#!/usr/bin/env python3
"""Tests for the opt-in residual-boundary capture reader."""
import struct
import tempfile
import unittest
from pathlib import Path

from compare_boundary_capture import HEADER, metrics, read_capture, read_capture_records


class BoundaryCaptureTests(unittest.TestCase):
    def test_reads_stbndy2_fields_and_geometry(self):
        # n_embd=2, hc=1 gives row=5 and total payload=14 float32 values.
        values = tuple(float(i) for i in range(14))
        header = HEADER.pack(b'STBNDY2\0', 2, 2, 7, 2, 1, 42, -1)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            path.write_bytes(header + struct.pack('<14f', *values))
            meta, fields = read_capture(path)
        self.assertEqual(meta, {'layer': 2, 'position': 7, 'n_embd': 2, 'hc': 1,
                                'token': 42, 'slot': -1})
        self.assertEqual(fields['layer_output_rt'], (0.0, 1.0))
        self.assertEqual(fields['layer_output_moe'], (2.0, 3.0))
        self.assertEqual(fields['layer_output_inj2'], (4.0,))
        self.assertEqual(fields['next_layer_rt'], (5.0, 6.0))
        self.assertEqual(fields['next_layer_xn'], (12.0, 13.0))

    def test_metrics_reports_exact_and_changed_values(self):
        self.assertEqual(metrics((1.0, 2.0), (1.0, 2.0))['different'], 0)
        changed = metrics((1.0, 2.0), (1.0, 3.0))
        self.assertEqual(changed['different'], 1)
        self.assertEqual(changed['max_abs'], 1.0)

    def test_rejects_truncated_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            path.write_bytes(HEADER.pack(b'STBNDY2\0', 2, 2, 7, 2, 1, 42, -1) + b'\0')
            with self.assertRaisesRegex(ValueError, 'payload'):
                read_capture(path)

    def test_reads_concatenated_layer_records(self):
        payload = struct.pack('<14f', *range(14))
        records = [HEADER.pack(b'STBNDY2\0', 2, layer, 7, 2, 1, 42, -1) + payload
                   for layer in (1, 3)]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            path.write_bytes(b''.join(records))
            decoded = read_capture_records(path)
        self.assertEqual([header['layer'] for header, _ in decoded], [1, 3])


if __name__ == '__main__':
    unittest.main()
