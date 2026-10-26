#!/usr/bin/env python3
"""Tests for Q8_1 activation representation comparisons."""
import struct
import tempfile
import unittest
from pathlib import Path

from compare_q8_1_activation_capture import compare_captures, compare_vectors


HEADER = struct.Struct('<8sIIIIQq8i')


def capture(path: Path, rows: list[tuple[int, int, tuple[float, ...]]]) -> None:
    with path.open('wb') as out:
        for position, token, values in rows:
            header = HEADER.pack(b'STMOINP1', 1, 3, 1, 0, len(values), position,
                                 token, 0, 0, 0, 0, 0, 0, 0)
            out.write(header)
            out.write(struct.pack(f'<{len(values)}f', *values))


class Q8_1ActivationCaptureTests(unittest.TestCase):
    def test_identical_vectors_have_identical_q8_1(self):
        values = tuple((i - 15) / 17 for i in range(32))
        result = compare_vectors(values, values)
        self.assertEqual(result['f32']['different'], 0)
        self.assertEqual(result['q8_1']['integer_codes_different'], 0)
        self.assertEqual(result['q8_1']['scales_different'], 0)

    def test_scale_rounding_change_is_reported_separately_from_codes(self):
        below, above = [], []
        # The maximum lies on opposite sides of a binary16 midpoint after /127.
        midpoint = (0.0083160400390625 + 0.00832366943359375) / 2
        center = midpoint * 127
        for value in (center,):
            bits = struct.unpack('<I', struct.pack('<f', value))[0]
            below.append(struct.unpack('<f', struct.pack('<I', bits - 1))[0])
            above.append(struct.unpack('<f', struct.pack('<I', bits + 1))[0])
        a = tuple([0.002] * 31 + below)
        b = tuple([0.002] * 31 + above)
        result = compare_vectors(a, b)['q8_1']
        self.assertEqual(result['integer_codes_different'], 0)
        self.assertEqual(result['scales_different'], 1)
        self.assertEqual(result['different_blocks'][0]['block'], 0)

    def test_capture_compare_joins_rows_by_position_and_token(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b = root / 'a.bin', root / 'b.bin'
            values = tuple((i - 15) / 17 for i in range(32))
            capture(a, [(12, 99, values), (13, 100, values)])
            capture(b, [(12, 99, values), (13, 100, values)])
            result = compare_captures(a, b, [13])
            self.assertEqual(len(result['positions']), 1)
            self.assertEqual(result['positions'][0]['position'], 13)
            self.assertEqual(result['positions'][0]['token_id'], 100)

    def test_capture_rejects_token_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b = root / 'a.bin', root / 'b.bin'
            values = tuple([0.0] * 32)
            capture(a, [(12, 99, values)])
            capture(b, [(12, 100, values)])
            with self.assertRaisesRegex(ValueError, 'identities differ'):
                compare_captures(a, b)


if __name__ == '__main__':
    unittest.main()
