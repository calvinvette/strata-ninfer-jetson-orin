"""Offline checks for the cache × context screen configuration builder."""
import unittest

from cache_context_screen import api_command, cell_configs, replace_option
from pathlib import Path


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
        self.assertEqual(cells[-1]['expert_cache_argument'], 5000)
        self.assertNotIn('requested_cache_lower_bound', cells[-1])

    def test_no_trace_is_opt_in_and_reaches_api_driver(self):
        root = Path('/tmp/cache-context-test')
        tools = root / 'tools'
        cfg = root / 'config.json'
        workloads = root / 'workloads.json'
        request = root / 'cell' / 'requests.json'
        traced = api_command(Path('/usr/bin/python3'), tools, cfg, workloads, request, 3)
        untraced = api_command(Path('/usr/bin/python3'), tools, cfg, workloads, request, 3, no_trace=True)
        self.assertNotIn('--no-trace', traced)
        self.assertEqual(untraced[-1], '--no-trace')
        self.assertEqual(untraced[untraced.index('--timeout') + 1], '1800')


if __name__ == '__main__':
    unittest.main()
