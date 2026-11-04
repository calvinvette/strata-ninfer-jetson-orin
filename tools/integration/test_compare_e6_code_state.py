#!/usr/bin/env python3
"""Tests for accepted-prefix parity comparisons on E6 code captures."""
import unittest

from compare_e6_code_state import compare_traces, check_quality


TRACE = [{"token_ids": [11], "state": {"gdn": "aa", "kv": "bb"}},
         {"token_ids": [12, 13], "state": {"gdn": "cc", "kv": "dd"}}]
CODE = ("def merge_ranges(ranges):\n"
        "    result = []\n"
        "    for start, end in sorted(ranges):\n"
        "        if result and start <= result[-1][1] + 1:\n"
        "            if end > result[-1][1]:\n"
        "                result[-1][1] = end\n"
        "        else:\n"
        "            result.append([start, end])\n"
        "    return result\n")


class CodeStateComparatorTests(unittest.TestCase):
    def test_equal_trace_reports_token_and_state_parity(self):
        result = compare_traces(TRACE, TRACE)
        self.assertTrue(result["token_ids_equal"])
        self.assertTrue(result["persistent_state_equal"])
        self.assertEqual(result["strata_committed_tokens"], 3)
        self.assertIsNone(result["first_difference"])

    def test_token_mismatch_is_reported(self):
        other = [{**TRACE[0], "token_ids": [99]}, TRACE[1]]
        result = compare_traces(TRACE, other)
        self.assertFalse(result["token_ids_equal"])
        self.assertTrue(result["persistent_state_equal"])
        self.assertEqual(result["first_difference"]["index"], 0)

    def test_state_mismatch_is_reported(self):
        other = [TRACE[0], {"token_ids": [12, 13], "state": {"gdn": "ff", "kv": "dd"}}]
        result = compare_traces(TRACE, other)
        self.assertFalse(result["persistent_state_equal"])
        self.assertEqual(result["first_difference"]["index"], 1)

    def test_different_trace_lengths_are_reported(self):
        result = compare_traces(TRACE, TRACE[:1])
        self.assertFalse(result["token_ids_equal"])
        self.assertFalse(result["persistent_state_equal"])
        self.assertEqual(result["first_difference"]["reason"], "trace lengths differ")


if __name__ == "__main__":
    unittest.main()
