#!/usr/bin/env python3
"""Tests for the independent E6 ledger aggregation oracle."""
import json
import unittest

from evaluate_e6_ledger_task import EXPECTED, evaluate_result, parse_answer


class EvaluateLedgerTaskTests(unittest.TestCase):
    def test_expected_json_passes(self):
        self.assertEqual(parse_answer(json.dumps(EXPECTED)), EXPECTED)

    def test_fenced_expected_json_passes(self):
        text = "```json\n" + json.dumps(EXPECTED) + "\n```"
        self.assertEqual(parse_answer(text), EXPECTED)

    def test_wrong_signed_sum_fails(self):
        wrong = {**EXPECTED, "total": {"count": 12, "sum": 86}}
        with self.assertRaises(AssertionError):
            parse_answer(json.dumps(wrong))

    def test_missing_region_fails(self):
        wrong = {**EXPECTED, "regions": {"EAST": EXPECTED["regions"]["EAST"]}}
        with self.assertRaises(AssertionError):
            parse_answer(json.dumps(wrong))

    def test_capture_records_all_outcomes(self):
        good = {"status": "pass", "cell": "ledger", "warmup": False,
                "response": {"choices": [{"message": {"content": json.dumps(EXPECTED)}}]}}
        failed = {"status": "pass", "cell": "ledger", "warmup": True,
                  "response": {"choices": [{"message": {"content": "{}"}}]}}
        result = evaluate_result({"checks": [good, failed]})
        self.assertFalse(result["all_passed"])
        self.assertEqual([row["passed"] for row in result["outcomes"]], [True, False])


if __name__ == "__main__":
    unittest.main()
