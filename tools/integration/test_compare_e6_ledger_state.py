#!/usr/bin/env python3
"""Tests for the E6 ledger accepted-prefix comparator."""
import unittest

from compare_e6_ledger_state import compare_traces


TRACE = [{"token_ids": [11], "state": {"gdn": "aa", "kv": "bb"}},
         {"token_ids": [12, 13], "state": {"gdn": "cc", "kv": "dd"}}]


class CompareLedgerTraceTests(unittest.TestCase):
    def test_matching_tokens_and_state_pass_comparison(self):
        result = compare_traces(TRACE, TRACE)
        self.assertTrue(result["token_ids_equal"])
        self.assertTrue(result["persistent_state_equal"])
        self.assertEqual(result["strata_committed_tokens"], 3)
        self.assertIsNone(result["first_difference"])

    def test_token_mismatch_is_reported(self):
        other = [{**TRACE[0], "token_ids": [99]}, TRACE[1]]
        result = compare_traces(TRACE, other)
        self.assertFalse(result["token_ids_equal"])
        self.assertEqual(result["first_difference"]["index"], 0)

    def test_state_mismatch_is_reported(self):
        other = [TRACE[0], {"token_ids": [12, 13], "state": {"gdn": "ff", "kv": "dd"}}]
        result = compare_traces(TRACE, other)
        self.assertFalse(result["persistent_state_equal"])
        self.assertEqual(result["first_difference"]["index"], 1)

    def test_length_mismatch_is_reported(self):
        result = compare_traces(TRACE, TRACE[:1])
        self.assertFalse(result["persistent_state_equal"])
        self.assertEqual(result["first_difference"]["reason"], "trace lengths differ")


if __name__ == "__main__":
    unittest.main()
