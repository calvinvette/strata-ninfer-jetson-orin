#!/usr/bin/env python3
"""Tests for opt-in GDN state capture argument parsing."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ninfer_q2_retrieval_check import (parse_gdn_commit_layer,
                                       repeated_staged_backend_arms,
                                       select_expert_backend,
                                       staged_backend_arms)


class GdnCommitLayerArgumentTests(unittest.TestCase):
    def test_all_layers_capture(self):
        self.assertEqual(parse_gdn_commit_layer('all'), 'all')

    def test_one_layer_capture(self):
        self.assertEqual(parse_gdn_commit_layer('13'), 13)

    def test_rejects_invalid_values(self):
        for value in ('many', '-1', '48'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_gdn_commit_layer(value)


class StagedBackendOrderTests(unittest.TestCase):
    def test_default_order_runs_strata_first(self):
        self.assertEqual(staged_backend_arms(), (
            ('strata-staged', 'strata', 0), ('ninfer-staged', 'ninfer', 0)))

    def test_reverse_order_runs_ninfer_first(self):
        self.assertEqual(staged_backend_arms(reverse=True), (
            ('ninfer-staged', 'ninfer', 0), ('strata-staged', 'strata', 0)))

    def test_same_backend_repeat_uses_two_fresh_arm_names(self):
        self.assertEqual(repeated_staged_backend_arms('strata'), (
            ('strata-repeat-1', 'strata', 0), ('strata-repeat-2', 'strata', 0)))
        self.assertEqual(repeated_staged_backend_arms('ninfer'), (
            ('ninfer-repeat-1', 'ninfer', 0), ('ninfer-repeat-2', 'ninfer', 0)))

    def test_same_backend_repeat_rejects_unknown_backend(self):
        with self.assertRaises(ValueError):
            repeated_staged_backend_arms('other')


class ExpertBackendSelectionTests(unittest.TestCase):
    def test_ninfer_arm_is_explicit_and_strict(self):
        self.assertEqual(select_expert_backend(
            ['--expert-backend', 'strata', '--prefill', '128'], 'ninfer'),
            ['--expert-backend', 'ninfer', '--prefill', '128',
             '--expert-backend-strict'])

    def test_strata_arm_removes_strict_mode(self):
        self.assertEqual(select_expert_backend(
            ['--expert-backend', 'ninfer', '--expert-backend-strict'], 'strata'),
            ['--expert-backend', 'strata'])

    def test_backend_is_added_when_config_omits_it(self):
        self.assertEqual(select_expert_backend(['--prefill', '128'], 'ninfer'),
                         ['--prefill', '128', '--expert-backend', 'ninfer',
                          '--expert-backend-strict'])

    def test_rejects_unknown_backend(self):
        with self.assertRaises(ValueError):
            select_expert_backend([], 'other')


if __name__ == '__main__':
    unittest.main()
