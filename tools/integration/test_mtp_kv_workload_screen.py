import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from mtp_kv_workload_screen import (bootstrap_interval, expected_answer,
                                    make_design, summarize_factorial)


class MtpKvWorkloadScreenTests(unittest.TestCase):
    def test_independent_answers_cover_sum_and_marker_only_tasks(self):
        short = {'cell': 'short', 'expected_codes': ['A-1', 'B-2', 'C-3'],
                 'expected_suffix_sum': 6}
        long = {'cell': 'long', 'expected_codes': ['D-4', 'E-5', 'F-6']}
        self.assertEqual(expected_answer(short), 'EARLY=A-1, MIDDLE=B-2, LATE=C-3, SUM=6')
        self.assertEqual(expected_answer(long), 'EARLY=D-4, MIDDLE=E-5, LATE=F-6')
        with self.assertRaises(ValueError):
            expected_answer({'cell': 'bad', 'expected_codes': ['only-two', 'codes']})

    def test_factorial_design_contains_each_arm_once_per_randomized_block(self):
        cells = make_design(['fp16', 'int8'], ['short', 'long'], [0, 4], 3, 19)
        self.assertEqual(len(cells), 24)
        for block in range(3):
            arms = [row for row in cells if row['block'] == block]
            self.assertEqual(len(arms), 8)
            self.assertEqual({(r['kv'], r['workload'], r['window']) for r in arms},
                             {(kv, workload, window)
                              for kv in ('fp16', 'int8')
                              for workload in ('short', 'long')
                              for window in (0, 4)})
            self.assertEqual(sorted(r['order'] for r in arms), list(range(8)))
        self.assertEqual(cells, make_design(['fp16', 'int8'], ['short', 'long'], [0, 4], 3, 19))

    def test_three_way_interaction_uses_within_block_ratios(self):
        rows = []
        for block in range(3):
            for kv in ('fp16', 'int8'):
                for workload in ('short', 'long'):
                    control = 100.0
                    effect = 1.1 if kv == 'fp16' else (1.2 if workload == 'short' else 1.32)
                    for window, value in ((0, control), (4, control * effect)):
                        rows.append({'block': block, 'kv': kv, 'workload': workload,
                                     'window': window,
                                     'metrics': {'prompt_tps': value, 'decode_tps': value,
                                                 'client_ttft_s': 1 / value,
                                                 'client_total_s': 1 / value}})
        result = summarize_factorial(rows, ['short', 'long'], ['fp16', 'int8'], [0, 4], 71)
        interaction = result['three_way_summary']['decode_tps']
        self.assertAlmostEqual(interaction['median_percent'], 10.0, places=9)
        for value in interaction['paired_values_percent']:
            self.assertAlmostEqual(value, 10.0, places=9)

    def test_bootstrap_interval_is_finite_for_three_paired_blocks(self):
        interval = bootstrap_interval([0.1, 0.2, 0.3], 7)
        self.assertLessEqual(interval[0], interval[1])
        self.assertGreaterEqual(interval[0], 0.1)
        self.assertLessEqual(interval[1], 0.3)


if __name__ == '__main__':
    unittest.main()
