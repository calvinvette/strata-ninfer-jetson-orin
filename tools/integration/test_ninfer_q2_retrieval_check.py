#!/usr/bin/env python3
"""Tests for opt-in GDN state capture argument parsing."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ninfer_q2_retrieval_check import parse_gdn_commit_layer, staged_backend_arms


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


if __name__ == '__main__':
    unittest.main()
