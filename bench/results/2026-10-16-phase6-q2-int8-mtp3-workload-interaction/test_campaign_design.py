"""CPU-only checks for randomized design and interaction math."""
from collections import defaultdict
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from campaign_plan import make_schedule, workload_filename
from analyze_interaction import interaction_interval, marker_check
from run_campaign import config_path, workload_path
from prepare_confirmation import make_body, NEEDLES


class CampaignDesignTests(unittest.TestCase):
    def test_each_campaign_arm_uses_an_existing_configuration(self):
        self.assertEqual(config_path("baseline").name, "config-mtp-off.json")
        self.assertEqual(config_path("candidate").name, "config-mtp3.json")
        self.assertTrue(config_path("baseline").is_file())
        self.assertTrue(config_path("candidate").is_file())

    def test_confirmation_workload_names_match_runner_paths(self):
        for name in ("short", "near_limit"):
            with self.subTest(name=name):
                self.assertEqual(workload_filename(name), workload_path("confirm", name).name)
                self.assertEqual(workload_filename(name), workload_path("screen", name).name)
                self.assertTrue((HERE / workload_filename(name)).is_file())

    def test_short_confirmation_prompt_explains_suffix_sum_oracle(self):
        prompt = make_body(26, NEEDLES["short"], 6, "short")
        self.assertIn("add the three numbers at the ends of those codes", prompt)
        self.assertIn("SUM=<sum of the three ending numbers>", prompt)
        expected = {"expected_codes": [code for _, code in NEEDLES["short"]],
                    "expected_suffix_sum": 1478}
        self.assertTrue(marker_check(
            "EARLY=CITRUS-AXLE-431, MIDDLE=MARBLE-THICKET-782, "
            "LATE=OXIDE-KITE-265, SUM=1478", expected)[0])

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
