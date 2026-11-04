#!/usr/bin/env python3
"""Tests for E6 code-task launch and oracle validation."""
import unittest

from summarize_e6_code_screen import config_for_comparison, quality_for_requests


BASE = {
    "exe": "/engine/strata", "args": ["--max-context", "16384", "--expert-cache", "5000"],
    "cwd": "/repo", "tokenizer": "/models/tokenizer", "model_name": "Strata",
    "log": "/tmp/strata.log", "port": 18000, "draft_vocab": "cjk",
    "env": {"STRATA_RESIDENT_HEADROOM_GIB": "9"},
}

CODE = ("def merge_ranges(ranges):\n"
        "    result = []\n"
        "    for start, end in sorted(ranges):\n"
        "        if result and start <= result[-1][1] + 1:\n"
        "            if end > result[-1][1]:\n"
        "                result[-1][1] = end\n"
        "        else:\n"
        "            result.append([start, end])\n"
        "    return result\n")


class CodeScreenTests(unittest.TestCase):
    def test_normalizes_only_backend_and_run_labels(self):
        candidate = {**BASE, "model_name": "NInfer", "log": "/tmp/ninfer.log", "port": 18001,
                     "args": BASE["args"] + ["--expert-backend", "ninfer", "--expert-backend-strict"]}
        self.assertEqual(config_for_comparison(BASE), config_for_comparison(candidate))

    def test_runtime_setting_difference_is_preserved(self):
        candidate = {**BASE, "args": BASE["args"] + ["--expert-backend", "ninfer",
                                                       "--expert-backend-strict", "--prefill", "256"]}
        self.assertNotEqual(config_for_comparison(BASE), config_for_comparison(candidate))

    def test_candidate_selector_must_be_strict_ninfer(self):
        candidate = {**BASE, "args": BASE["args"] + ["--expert-backend", "fallback"]}
        with self.assertRaisesRegex(ValueError, "not strict NInfer"):
            config_for_comparison(candidate)

    def test_exact_code_oracle_accepts_two_matching_requests(self):
        requests = {"checks": [
            {"cell": "code", "warmup": True, "status": "pass",
             "response": {"usage": {"prompt_tokens": 8192}, "choices": [{"message": {"content": CODE}}]}},
            {"cell": "code", "warmup": False, "status": "pass",
             "response": {"usage": {"prompt_tokens": 8192}, "choices": [{"message": {"content": CODE}}]}},
        ]}
        result = quality_for_requests(requests, "code", 8192)
        self.assertTrue(result["all_passed"])
        self.assertEqual(len(result["outcomes"]), 2)

    def test_prompt_count_mismatch_fails_oracle_gate(self):
        requests = {"checks": [{"cell": "code", "warmup": True, "status": "pass",
                                 "response": {"usage": {"prompt_tokens": 8191},
                                               "choices": [{"message": {"content": CODE}}]}}]}
        self.assertFalse(quality_for_requests(requests, "code", 8192)["all_passed"])


if __name__ == "__main__":
    unittest.main()
