import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from mtp_continuation_probe import rejected_drafts, summarize_rejections


class MtpContinuationProbeTests(unittest.TestCase):
    def test_counts_rejected_drafts(self):
        self.assertEqual(rejected_drafts({'drafts_offered': 9, 'drafts_accepted': 6}), 3)

    def test_zero_when_no_mtp_drafts_were_offered(self):
        self.assertEqual(rejected_drafts({'drafts_offered': 0, 'drafts_accepted': 0}), 0)

    def test_rejects_impossible_accepted_count(self):
        with self.assertRaises(ValueError):
            rejected_drafts({'drafts_offered': 2, 'drafts_accepted': 3})

    def test_requires_a_rejection_before_the_recovery_request(self):
        result = summarize_rejections(
            {'drafts_offered': 15, 'drafts_accepted': 6},
            {'drafts_offered': 6, 'drafts_accepted': 6},
            {'drafts_offered': 9, 'drafts_accepted': 4})
        self.assertTrue(result['rejection_before_recovery'])
        self.assertEqual(result['rejected_drafts_by_request'],
                         {'initial': 9, 'continuation': 0, 'recovery': 5})

    def test_rejects_sequences_without_any_pre_recovery_rejection(self):
        result = summarize_rejections(
            {'drafts_offered': 0, 'drafts_accepted': 0},
            {'drafts_offered': 6, 'drafts_accepted': 6},
            {'drafts_offered': 9, 'drafts_accepted': 4})
        self.assertFalse(result['rejection_before_recovery'])


if __name__ == '__main__':
    unittest.main()
