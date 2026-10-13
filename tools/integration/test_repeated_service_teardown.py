"""Offline checks for fresh-service teardown cycle configuration."""
import unittest
from pathlib import Path

from repeated_service_teardown import cycle_config


class RepeatedServiceTeardownTest(unittest.TestCase):
    def test_cycle_config_isolated_port_and_log_without_source_mutation(self):
        source = {'port': 18764, 'log': 'old.log', 'args': ['--serve']}
        cycle = cycle_config(source, 18842, Path('/tmp/cycle-02'))
        self.assertEqual(cycle['port'], 18842)
        self.assertTrue(cycle['log'].endswith('/cycle-02/engine.log'))
        self.assertEqual(cycle['args'], ['--serve'])
        self.assertEqual(source, {'port': 18764, 'log': 'old.log', 'args': ['--serve']})


if __name__ == '__main__':
    unittest.main()
