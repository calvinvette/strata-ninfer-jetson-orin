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

    def test_single_followup_block_contains_each_factorial_arm_once(self):
        cells = make_design(['fp16', 'int8'], ['short', 'long'], [0, 4], 1, 20261025)
        self.assertEqual(len(cells), 8)
        self.assertEqual({(x['kv'], x['workload'], x['window']) for x in cells},
                         {(kv, work, window) for kv in ('fp16', 'int8')
                          for work in ('short', 'long') for window in (0, 4)})

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

    def test_single_followup_block_keeps_unavailable_bootstrap_interval_null(self):
        rows = []
        for kv in ('fp16', 'int8'):
            for workload in ('short', 'long'):
                for window, factor in ((0, 1.0), (4, 1.1)):
                    value = 100.0 * factor
                    rows.append({'block': 0, 'kv': kv, 'workload': workload,
                                 'window': window,
                                 'metrics': {'prompt_tps': value, 'decode_tps': value,
                                             'client_ttft_s': 1 / value,
                                             'client_total_s': 1 / value}})
        result = summarize_factorial(rows, ['short', 'long'], ['fp16', 'int8'], [0, 4], 9)
        self.assertEqual(
            result['cell_effects'][0]['prompt_tps_paired_bootstrap_95_interval_percent'],
            [None, None])
        self.assertEqual(
            result['three_way_summary']['decode_tps']['paired_bootstrap_95_interval_percent'],
            [None, None])

    def test_single_workload_screen_reports_only_estimable_interactions(self):
        rows = []
        for kv in ('fp16', 'int8'):
            for window, factor in ((0, 1.0), (4, 1.1)):
                value = 100.0 * factor
                rows.append({'block': 0, 'kv': kv, 'workload': 'heldout',
                             'window': window,
                             'metrics': {'prompt_tps': value, 'decode_tps': value,
                                         'client_ttft_s': 1 / value,
                                         'client_total_s': 1 / value}})
        result = summarize_factorial(rows, ['heldout'], ['fp16', 'int8'], [0, 4], 11)
        self.assertEqual(len(result['cell_effects']), 2)
        self.assertEqual(len(result['mtp_by_kv_interactions']), 1)
        self.assertEqual(result['mtp_by_workload_interactions'], [])
        self.assertEqual(result['three_way_interactions'], [])

    def test_bootstrap_interval_is_finite_for_three_paired_blocks(self):
        interval = bootstrap_interval([0.1, 0.2, 0.3], 7)
        self.assertLessEqual(interval[0], interval[1])
        self.assertGreaterEqual(interval[0], 0.1)
        self.assertLessEqual(interval[1], 0.3)

    def test_resume_skips_passed_arm_and_retries_pressure_abort_without_overwrite(self):
        from tempfile import TemporaryDirectory
        from mtp_kv_workload_screen import attempt_name

        cell = {'block': 2, 'kv': 'fp16', 'workload': 'long', 'window': 4}
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            base = 'block-02-kv-fp16-workload-long-mtp-4'
            self.assertEqual(attempt_name(cell, [], output), base)
            passed = [dict(cell, status='pass', directory=base)]
            self.assertIsNone(attempt_name(cell, passed, output))

            aborted = [dict(cell, status='fail', supervisor_status='pressure_abort',
                            directory=base)]
            self.assertEqual(attempt_name(cell, aborted, output), base + '-retry-01')
            (output / (base + '-retry-01')).mkdir()
            self.assertEqual(attempt_name(cell, aborted, output), base + '-retry-02')

    def test_resume_refuses_to_silently_retry_non_pressure_failure(self):
        from tempfile import TemporaryDirectory
        from mtp_kv_workload_screen import attempt_name

        cell = {'block': 0, 'kv': 'int8', 'workload': 'short', 'window': 4}
        prior = [dict(cell, status='fail', supervisor_status='pass',
                      directory='failed-quality-check')]
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'did not end in a pressure abort'):
                attempt_name(cell, prior, Path(temporary))


if __name__ == '__main__':
    unittest.main()
