import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from mtp_continuation_probe import rejected_drafts


class MtpContinuationProbeTests(unittest.TestCase):
    def test_counts_rejected_drafts(self):
        self.assertEqual(rejected_drafts({'drafts_offered': 9, 'drafts_accepted': 6}), 3)

    def test_zero_when_no_mtp_drafts_were_offered(self):
        self.assertEqual(rejected_drafts({'drafts_offered': 0, 'drafts_accepted': 0}), 0)

    def test_rejects_impossible_accepted_count(self):
        with self.assertRaises(ValueError):
            rejected_drafts({'drafts_offered': 2, 'drafts_accepted': 3})


if __name__ == '__main__':
    unittest.main()
