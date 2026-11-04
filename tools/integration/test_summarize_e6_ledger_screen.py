#!/usr/bin/env python3
"""Tests for strict launch normalization in the E6 ledger screen analyzer."""
import unittest

from summarize_e6_ledger_screen import config_for_comparison


BASE = {
    "exe": "/engine/strata",
    "args": ["--max-context", "8192", "--expert-cache", "5000"],
    "cwd": "/repo",
    "tokenizer": "/models/tokenizer",
    "model_name": "API Strata label",
    "log": "/tmp/strata.log",
    "port": 18987,
    "draft_vocab": "cjk",
    "env": {"STRATA_RESIDENT_HEADROOM_GIB": "9"},
}


class ConfigNormalizationTests(unittest.TestCase):
    def test_backend_flags_and_per_process_labels_are_the_only_differences(self):
        candidate = {**BASE, "model_name": "API NInfer label", "log": "/tmp/ninfer.log", "port": 18988,
                     "args": BASE["args"] + ["--expert-backend", "ninfer", "--expert-backend-strict"]}
        self.assertEqual(config_for_comparison(BASE), config_for_comparison(candidate))

    def test_unexpected_runtime_flag_difference_is_not_normalized(self):
        candidate = {**BASE, "args": BASE["args"] + ["--expert-backend", "ninfer",
                                                         "--expert-backend-strict", "--prefill", "256"]}
        self.assertNotEqual(config_for_comparison(BASE), config_for_comparison(candidate))

    def test_unknown_ninfer_selector_is_rejected(self):
        candidate = {**BASE, "args": BASE["args"] + ["--expert-backend", "fallback"]}
        with self.assertRaisesRegex(ValueError, "not strict NInfer"):
            config_for_comparison(candidate)


if __name__ == "__main__":
    unittest.main()
