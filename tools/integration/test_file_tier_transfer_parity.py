"""Tests for isolated cgroup I/O counter parsing."""
import tempfile
import unittest
from pathlib import Path

from file_tier_transfer_parity import (actual_expert_cache_slots, cgroup_io_read_bytes,
                                      transfer_modes)


class TransferModeTests(unittest.TestCase):
    def test_prefetch_stage_pair_holds_io_path_constant(self):
        self.assertEqual(transfer_modes(True), [
            ('prefetch-fill', '1', '0'), ('prefetch-stage', '1', '1')])

    def test_original_mapped_and_pread_pair_is_unchanged(self):
        self.assertEqual(transfer_modes(False), [('mapped', '0', '0'), ('pread', '1', '0')])


class CgroupIoReadBytesTests(unittest.TestCase):
    def test_sums_read_bytes_across_devices_and_ignores_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaf = Path(tmp) / 'system.slice' / 'test.scope'
            leaf.mkdir(parents=True)
            (leaf / 'io.stat').write_text(
                '259:0 rbytes=1048576 wbytes=2097152 rios=3 wios=4 dbytes=0 dios=0\n'
                '7:18 rbytes=512 wbytes=1024 rios=1 wios=2 dbytes=0 dios=0\n')
            got = cgroup_io_read_bytes('0::/system.slice/test.scope\n', tmp)
        self.assertEqual(got, 1048576 + 512)

    def test_rejects_non_unified_cgroup_without_io_stat(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StopIteration):
                cgroup_io_read_bytes('2:cpu:/user.slice\n', tmp)


class ActualExpertCacheSlotsTests(unittest.TestCase):
    def test_reads_one_reported_capacity(self):
        self.assertEqual(actual_expert_cache_slots(
            'strata generate: expert cache 3903 slots, 7 GiB allocated\n'), 3903)

    def test_rejects_missing_or_conflicting_capacity(self):
        self.assertIsNone(actual_expert_cache_slots('startup without cache report'))
        self.assertIsNone(actual_expert_cache_slots(
            'expert cache 3903 slots\nexpert cache 6519 slots\n'))


if __name__ == '__main__':
    unittest.main()
