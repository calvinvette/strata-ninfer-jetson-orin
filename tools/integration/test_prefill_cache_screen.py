"""Offline checks for the cache-budget × prefill-chunk screen."""
import unittest
from pathlib import Path

from prefill_cache_screen import prefill_cache_configs


class PrefillCacheScreenTest(unittest.TestCase):
    def test_builds_factor_grid_without_mutating_source(self):
        source = {'args': ['--expert-cache', '3000', '--prefill', '64',
                           '--max-context', '8192']}
        cells = prefill_cache_configs(source, [3000, 5000], [32, 128])
        self.assertEqual([cell['name'] for cell in cells], [
            'cache3000-prefill32', 'cache3000-prefill128',
            'cache5000-prefill32', 'cache5000-prefill128'])
        self.assertEqual(source['args'], ['--expert-cache', '3000', '--prefill', '64',
                                          '--max-context', '8192'])
        self.assertEqual(cells[-1]['expert_cache_argument'], 5000)
        self.assertEqual(cells[-1]['prefill_chunk_tokens'], 128)
        self.assertEqual(cells[-1]['config']['args'], [
            '--expert-cache', '5000', '--prefill', '128', '--max-context', '8192'])


if __name__ == '__main__':
    unittest.main()
