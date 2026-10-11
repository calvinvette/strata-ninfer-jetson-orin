import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from stage_buffer_parity import paired_ratio_effect, stage_environment


class StageBufferEnvironmentTests(unittest.TestCase):
    def test_timing_mode_removes_inherited_trace_instrumentation(self):
        source = {'STRATA_TRACE': '1', 'STRATA_STATE_HASH': '1',
                  'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_HASH_GDN': '1',
                  'STRATA_PREFILL_CPU_SHARE': '0'}
        env = stage_environment(source, '1', timing_only=True)
        self.assertEqual(env, {'STRATA_STAGE_PIN': '1', 'STRATA_MTP_BATCH': '1',
                               'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_IO_PREFETCH': '1',
                               'STRATA_IO_PF_STAGE': '1'})
        self.assertEqual(source['STRATA_TRACE'], '1')

    def test_correctness_mode_enables_state_and_owner_observations(self):
        env = stage_environment({'STRATA_PREFILL_CPU_SHARE': '0'}, '0')
        self.assertEqual(env['STRATA_STAGE_PIN'], '0')
        self.assertEqual(env['STRATA_STATE_HASH'], '1')
        self.assertEqual(env['STRATA_STATE_HASH_GDN'], '1')
        self.assertEqual(env['STRATA_INTEGRATION_TRACE'], '1')

    def test_paired_ratio_bootstrap_preserves_pairing(self):
        result = paired_ratio_effect([100.0, 200.0, 400.0],
                                     [80.0, 220.0, 360.0], iterations=1000, seed=7)
        for actual, expected in zip(result['pair_deltas_pct'], [-20.0, 10.0, -10.0]):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(result['paired_median_delta_pct'], -10.0)
        self.assertEqual(result['pairs'], 3)

    def test_paired_ratio_requires_positive_matched_samples(self):
        for control, candidate in (([], []), ([1.0], []), ([0.0], [1.0])):
            with self.subTest(control=control, candidate=candidate), self.assertRaises(ValueError):
                paired_ratio_effect(control, candidate, iterations=10)


if __name__ == '__main__':
    unittest.main()
