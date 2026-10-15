"""Offline checks for the cache-budget × prefill-chunk screen."""
import unittest
from pathlib import Path

from cache_context_screen import api_command
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

    def test_clock_sampling_is_enabled_on_supervisor(self):
        command = api_command(Path('/usr/bin/python3'), Path('/repo/tools/integration'),
                              Path('/tmp/config.json'), Path('/tmp/workload.json'),
                              Path('/tmp/requests.json'), 1, sample_clocks=True)
        separator = command.index('--')
        self.assertIn('--sample-clocks', command[:separator])
        self.assertNotIn('--sample-clocks', command[separator + 1:])

    def test_clock_sampling_is_opt_in(self):
        command = api_command(Path('/usr/bin/python3'), Path('/repo/tools/integration'),
                              Path('/tmp/config.json'), Path('/tmp/workload.json'),
                              Path('/tmp/requests.json'), 3)
        self.assertNotIn('--sample-clocks', command)


if __name__ == '__main__':
    unittest.main()
