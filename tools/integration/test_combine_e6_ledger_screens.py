import json
from pathlib import Path
import tempfile
import unittest

import combine_e6_ledger_screens as module


class CombineScreensTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.metric_names = module.METRICS

    def tearDown(self):
        self.tmp.cleanup()

    def screen(self, name, candidate_scale=1.01, max_context=8192, answer="same"):
        folder = self.root / name
        folder.mkdir()
        summary_path = folder / "summary.json"
        evidence_path = folder / "evidence.json"
        pairs = []
        for block in range(3):
            baseline_metrics = {metric: 10.0 + block for metric in self.metric_names}
            candidate_metrics = {metric: value * candidate_scale
                                 for metric, value in baseline_metrics.items()}
            arm = lambda values: {
                "metrics": values,
                "answer_sha256": answer,
                "completion_tokens": 12,
            }
            pairs.append({
                "block": block,
                "api_responses_identical": True,
                "arms": {
                    "baseline": arm(baseline_metrics),
                    "candidate": arm(candidate_metrics),
                },
            })
        summary_path.write_text(json.dumps({
            "paired_blocks": 3,
            "api_content_matching_blocks": 3,
            "fixture_sha256": "fixture",
            "cell": "ledger",
            "pairs": pairs,
        }))
        controls = {key: "fixed" for key in module.CONTROL_KEYS}
        controls["max_context"] = max_context
        controls["randomized_seed"] = 1 if name == "first" else 2
        evidence_path.write_text(json.dumps({
            "date": "2026-11-04",
            "hardware": "orin",
            "system": {"cuda": "12.6"},
            "runtime_binary_sha256": "binary",
            "model": "q2_0",
            "model_files": ["weights"],
            "task": {
                "name": "ledger",
                "family": "aggregation",
                "prompt_tokens": 2048,
                "generation_limit": 256,
                "allow_natural_stop": True,
                "fixture_sha256": "fixture",
                "quality_oracle": "exact",
            },
            "controls": controls,
        }))
        return summary_path, evidence_path

    def test_combines_only_equivalent_screens_and_keeps_all_pairs(self):
        screens = [self.screen("first", 1.01), self.screen("second", 0.99)]
        result = module.combine(screens)
        self.assertEqual(result["paired_blocks"], 6)
        self.assertEqual(len(result["metrics"]["decode_tps"]["pairs"]), 6)
        self.assertAlmostEqual(
            result["metrics"]["decode_tps"]["paired_median_effect_percent"], 0.0
        )

    def test_rejects_a_different_context_cap(self):
        screens = [self.screen("first"), self.screen("second", max_context=16384)]
        with self.assertRaisesRegex(ValueError, "screen control differs: max_context"):
            module.combine(screens)

    def test_rejects_reusing_a_randomized_seed(self):
        screens = [self.screen("first"), self.screen("second")]
        second_evidence = json.loads(screens[1][1].read_text())
        second_evidence["controls"]["randomized_seed"] = 1
        screens[1][1].write_text(json.dumps(second_evidence))
        with self.assertRaisesRegex(ValueError, "distinct randomized seeds"):
            module.combine(screens)

    def test_rejects_different_answer_across_screens(self):
        screens = [self.screen("first"), self.screen("second", answer="other")]
        with self.assertRaisesRegex(ValueError, "answers or output lengths differ"):
            module.combine(screens)


if __name__ == "__main__":
    unittest.main()
