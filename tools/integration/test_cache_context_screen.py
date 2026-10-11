"""Offline checks for the cache × context screen configuration builder."""
import unittest

from cache_context_screen import cell_configs, replace_option


class CacheContextScreenTest(unittest.TestCase):
    def test_replaces_only_the_selected_options_and_preserves_other_args(self):
        args = ['--expert-cache', '3000', '--prefill', '64', '--max-context', '4096']
        self.assertEqual(replace_option(args, '--max-context', 8192),
                         ['--expert-cache', '3000', '--prefill', '64', '--max-context', '8192'])

    def test_rejects_missing_or_duplicate_options(self):
        with self.assertRaises(ValueError):
            replace_option(['--prefill', '64'], '--expert-cache', 5000)
        with self.assertRaises(ValueError):
            replace_option(['--max-context', '4096', '--max-context', '8192'], '--max-context', 16384)

    def test_builds_full_factor_grid_without_mutating_source(self):
        source = {'args': ['--expert-cache', '3000', '--max-context', '4096', '--prefill', '64']}
        cells = cell_configs(source, [3000, 5000], [4096, 8192])
        self.assertEqual([c['name'] for c in cells], [
            'cache3000-ctx4096', 'cache3000-ctx8192',
            'cache5000-ctx4096', 'cache5000-ctx8192'])
        self.assertEqual(source['args'], ['--expert-cache', '3000', '--max-context', '4096', '--prefill', '64'])
        self.assertEqual(cells[-1]['config']['args'], ['--expert-cache', '5000', '--max-context', '8192', '--prefill', '64'])


if __name__ == '__main__':
    unittest.main()
