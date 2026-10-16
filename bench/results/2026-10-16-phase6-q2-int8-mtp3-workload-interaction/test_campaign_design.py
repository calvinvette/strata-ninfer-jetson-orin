"""CPU-only checks for randomized design and interaction math."""
from collections import defaultdict
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from campaign_plan import make_schedule
from analyze_interaction import interaction_interval, marker_check


class CampaignDesignTests(unittest.TestCase):
    def test_screen_and_confirmation_are_complete_randomized_pairs(self):
        for repetitions in (3, 7):
            with self.subTest(repetitions=repetitions):
                rows = make_schedule(repetitions, 20261016)
                self.assertEqual(len(rows), 4 * repetitions)
                self.assertEqual(rows, make_schedule(repetitions, 20261016))
                pairs = defaultdict(list)
                for row in rows:
                    pairs[(row["workload"], row["replicate"])].append(row["variant"])
                self.assertEqual(len(pairs), 2 * repetitions)
                self.assertTrue(all(sorted(arms) == ["baseline", "candidate"]
                                    for arms in pairs.values()))
                for workload in ("short", "near_limit"):
                    self.assertEqual(sum(key[0] == workload for key in pairs), repetitions)
                self.assertGreater(len({tuple(arms) for arms in pairs.values()}), 1)

    def test_quality_oracle_requires_unique_ordered_markers_and_sum(self):
        expected = {"expected_codes": ["EARLY-431", "MIDDLE-782", "LATE-265"],
                    "expected_suffix_sum": 1478}
        self.assertTrue(marker_check("EARLY-431 MIDDLE-782 LATE-265 SUM=1478", expected)[0])
        self.assertFalse(marker_check("EARLY-431 LATE-265 MIDDLE-782 SUM=1478", expected)[0])
        self.assertFalse(marker_check("EARLY-431 EARLY-431 MIDDLE-782 LATE-265 SUM=1478", expected)[0])
        self.assertFalse(marker_check("EARLY-431 MIDDLE-782 LATE-265 SUM=1477", expected)[0])

    def test_interaction_interval_is_ratio_of_workload_effects(self):
        short = [1.10] * 7
        long = [1.21] * 7
        low, high = interaction_interval(short, long, 42)
        self.assertAlmostEqual(low, 1.1)
        self.assertAlmostEqual(high, 1.1)


if __name__ == "__main__":
    unittest.main()
