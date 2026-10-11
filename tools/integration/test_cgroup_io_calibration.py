"""Unit checks for scoped cgroup I/O calibration."""
import tempfile
import unittest
from pathlib import Path

from cgroup_io_calibration import cgroup_scope, io_stat, read_byte_deltas


class CgroupIoCalibrationTests(unittest.TestCase):
    def test_finds_unified_scope(self):
        self.assertEqual(cgroup_scope('2:cpu:/legacy\n0::/user.slice/run.scope', Path('/cg')),
                         Path('/cg/user.slice/run.scope'))

    def test_requires_unified_scope(self):
        with self.assertRaisesRegex(ValueError, 'unified'):
            cgroup_scope('2:cpu:/legacy', Path('/cg'))

    def test_parses_read_bytes_by_device(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'io.stat'
            path.write_text('259:0 rbytes=67108864 wbytes=0 rios=16\n8:0 rbytes=12\n')
            self.assertEqual(io_stat(path), {
                '259:0': {'rbytes': 67108864, 'wbytes': 0, 'rios': 16},
                '8:0': {'rbytes': 12},
            })

    def test_read_delta_uses_device_rows_reported_by_cgroup(self):
        before = {'259:0': {'rbytes': 4_000}, '259:1': {'rbytes': 0}}
        after = {'259:0': {'rbytes': 64 * 1024 * 1024 + 4_000}}
        self.assertEqual(read_byte_deltas(before, after), {'259:0': 64 * 1024 * 1024,
                                                           '259:1': 0})


if __name__ == '__main__':
    unittest.main()
