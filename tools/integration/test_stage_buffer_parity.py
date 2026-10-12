import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from stage_buffer_parity import (context_reservation, paired_ratio_effect, stage_environment, state_hashes,
                                 stamp_arm_end, stamp_arm_start,
                                 warmup_completions_equal)


class StageBufferEnvironmentTests(unittest.TestCase):
    def test_context_reservation_leaves_request_margin_and_minimum(self):
        self.assertEqual(context_reservation(512, 8), 8192)
        self.assertEqual(context_reservation(8192, 8), 8232)

    def test_timing_mode_removes_inherited_trace_instrumentation(self):
        source = {'STRATA_TRACE': '1', 'STRATA_STATE_HASH': '1',
                  'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_HASH_GDN': '1',
                  'LD_PRELOAD': '/tmp/instrumentation.so',
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

    def test_arm_window_has_ordered_wall_and_monotonic_timestamps(self):
        arm = {}
        stamp_arm_start(arm)
        stamp_arm_end(arm)
        self.assertLessEqual(arm['started_wall_s'], arm['finished_wall_s'])
        self.assertLessEqual(arm['started_monotonic_s'], arm['finished_monotonic_s'])

    def test_warmup_and_measured_fingerprints_select_measured_state(self):
        keys = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
        first = dict(zip(keys, ('172',) + ('1a',) * 7 + ('1,2',)))
        last = dict(zip(keys, ('512',) + ('2b',) * 7 + ('3,4',)))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'engine.log'
            path.write_text('strata serve: STATE_HASH ' + ' '.join(f'{k}={v}' for k, v in first.items()) + '\n' +
                            'strata serve: STATE_HASH ' + ' '.join(f'{k}={v}' for k, v in last.items()) + '\n')
            self.assertEqual(state_hashes(path, expected_count=2), last)

    def test_rejects_unexpected_state_fingerprint_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'engine.log'
            path.write_text('strata serve: STATE_HASH L=512 gdn=aa ple=aa tail=aa dead=aa '
                            'pooled=aa pooled_full=aa kv=aa ple_prev=1,2\n')
            with self.assertRaisesRegex(ValueError, 'expected 2'):
                state_hashes(path, expected_count=2)

    def test_warmup_completion_must_match_across_staging_arms(self):
        same = {'prompt_sha256': 'prompt', 'ids_sha256': 'ids', 'generated_tokens': 64}
        diff = {'prompt_sha256': 'prompt', 'ids_sha256': 'other', 'generated_tokens': 64}
        self.assertTrue(warmup_completions_equal({'warmup': same}, {'warmup': same}))
        self.assertFalse(warmup_completions_equal({'warmup': same}, {'warmup': diff}))
        self.assertIsNone(warmup_completions_equal({}, {}))


if __name__ == '__main__':
    unittest.main()
