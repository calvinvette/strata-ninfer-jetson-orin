import struct
import tempfile
import unittest
from pathlib import Path

from compare_moe_bundle import HEADER, read_bundle, metrics


def record(layer, position, ids, weights, input_values, parts, shared, combined, k=2, n=3, token=17):
    header = HEADER.pack(b'STMOEBN1', 1, layer, k, 0, n, position, -1, token)
    payload = struct.pack(f'<{k}i', *ids)
    for values in (weights, input_values, parts, shared, combined):
        payload += struct.pack(f'<{len(values)}f', *values)
    return header + payload


class MoeBundleCompareTests(unittest.TestCase):
    def test_reads_concatenated_records_and_all_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            path.write_bytes(record(1, 99, [3, 5], [.6, .4], [1, 2, 3],
                                    [1, 2, 3, 4, 5, 6], [2, 3, 4], [3, 4, 5]) +
                            record(7, 99, [2, 4], [.7, .3], [4, 5, 6],
                                    [6, 5, 4, 3, 2, 1], [4, 5, 6], [5, 6, 7]))
            result = read_bundle(path)
            self.assertEqual(set(result), {(1, 99, -1, 17), (7, 99, -1, 17)})
            self.assertEqual(result[(7, 99, -1, 17)][1]['route_ids'], (2, 4))
            self.assertEqual(len(result[(1, 99, -1, 17)][1]['expert_parts']), 6)

    def test_pairs_distinct_tokens_at_the_same_layer_position(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            payload = record(0, 81, [3, 5], [.6, .4], [1, 2, 3],
                             [1, 2, 3, 4, 5, 6], [2, 3, 4], [3, 4, 5], token=3439)
            payload += record(0, 81, [2, 4], [.7, .3], [4, 5, 6],
                              [6, 5, 4, 3, 2, 1], [4, 5, 6], [5, 6, 7], token=2912)
            path.write_bytes(payload)
            result = read_bundle(path)
            self.assertEqual(set(result), {(0, 81, -1, 3439), (0, 81, -1, 2912)})

    def test_rejects_exact_duplicate_record_key(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            payload = record(0, 81, [3, 5], [.6, .4], [1, 2, 3],
                             [1, 2, 3, 4, 5, 6], [2, 3, 4], [3, 4, 5])
            path.write_bytes(payload + payload)
            with self.assertRaisesRegex(ValueError, 'duplicate MoE bundle record'):
                read_bundle(path)

    def test_metrics_report_bitwise_difference_and_scale(self):
        exact = metrics((1.0, 2.0), (1.0, 2.0))
        self.assertEqual(exact['different'], 0)
        changed = metrics((1.0, 2.0), (1.0, 2.25))
        self.assertEqual(changed['different'], 1)
        self.assertAlmostEqual(changed['max_abs'], .25)
        self.assertGreater(changed['relative_l2'], 0)

    def test_rejects_truncated_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture.bin'
            path.write_bytes(HEADER.pack(b'STMOEBN1', 1, 0, 2, 0, 3, 1, -1, 9))
            with self.assertRaisesRegex(ValueError, 'truncated STMOEBN1 payload'):
                read_bundle(path)


if __name__ == '__main__':
    unittest.main()
