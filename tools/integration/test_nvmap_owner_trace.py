"""CPU-only tests for the Tegra NVMap client-table parser."""
import unittest

from nvmap_owner_trace import parse_clients, parse_size_bytes


class NvmapTraceTests(unittest.TestCase):
    def test_size_units(self):
        self.assertEqual(parse_size_bytes('512K'), 512 * 1024)
        self.assertEqual(parse_size_bytes('1.5M'), 3 * 1024 ** 2 // 2)

    def test_client_rows_ignore_headers_and_totals(self):
        text = ('CLIENT                        PROCESS      PID        SIZE\n'
                'user                  strata_cuda_mem  2708535     614248K\n'
                'root                  compositor      42          1.5M\n'
                'total                                                   615784K\n')
        self.assertEqual(parse_clients(text), [
            {'client': 'user', 'process': 'strata_cuda_mem', 'pid': 2708535,
             'size_bytes': 614248 * 1024},
            {'client': 'root', 'process': 'compositor', 'pid': 42,
             'size_bytes': 3 * 1024 ** 2 // 2},
        ])


if __name__ == '__main__':
    unittest.main()
