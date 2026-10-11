import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from mtp_window_screen import (canonical_args, one_measured, select_workload,
                               validate_mtp_arm_args)


class MtpWindowScreenTests(unittest.TestCase):
    def test_canonical_args_only_ignores_mtp_selection(self):
        off = ['--pack', 'p', '--spec', '2', '--prompt-cache', '0']
        candidate = ['--pack', 'p', '--spec', '4', '--mtp', 'm', '--mtp-max-t', '4', '--prompt-cache', '0']
        self.assertEqual(canonical_args(off), canonical_args(candidate))
        candidate[candidate.index('--prompt-cache') + 1] = '6'
        self.assertNotEqual(canonical_args(off), canonical_args(candidate))

    def test_canonical_args_retains_feature_flags(self):
        a = ['--pack', 'p', '--spec', '4', '--mtp', 'm', '--no-prefill-borrow']
        b = ['--pack', 'p', '--spec', '2', '--no-prefill-borrow']
        self.assertEqual(canonical_args(a), canonical_args(b))
        b.remove('--no-prefill-borrow')
        self.assertNotEqual(canonical_args(a), canonical_args(b))

    def test_requires_one_measured_row(self):
        with __import__('tempfile').TemporaryDirectory() as directory:
            path = Path(directory) / 'requests.json'
            path.write_text('{"checks": [{"warmup": true}, {"warmup": false, "cell": "x"}]}')
            self.assertEqual(one_measured(path)['cell'], 'x')
            path.write_text('{"checks": [{"warmup": false}, {"warmup": false}]}')
            with self.assertRaises(ValueError):
                one_measured(path)

    def test_selects_named_workload_from_multi_cell_file(self):
        rows = {'workloads': [{'cell': 'short'}, {'cell': 'long'}]}
        self.assertEqual(select_workload(rows, 'long'), {'cell': 'long'})
        with self.assertRaises(ValueError):
            select_workload(rows)
        with self.assertRaises(ValueError):
            select_workload(rows, 'missing')

    def test_mtp_window_requires_existing_draft_weights(self):
        with __import__('tempfile').TemporaryDirectory() as directory:
            weights = Path(directory) / 'mtp.bin'
            weights.write_bytes(b'weights')
            validate_mtp_arm_args(['--spec', '2', '--mtp', str(weights),
                                   '--mtp-max-t', '2'], 2)
            validate_mtp_arm_args(['--spec', '2'], 0)
            with self.assertRaises(ValueError):
                validate_mtp_arm_args(['--spec', '2', '--mtp-max-t', '2'], 2)
            with self.assertRaises(ValueError):
                validate_mtp_arm_args(['--spec', '2', '--mtp', str(weights),
                                       '--mtp-max-t', '3'], 2)
            with self.assertRaises(ValueError):
                validate_mtp_arm_args(['--spec', '2', '--mtp', str(weights)], 0)


if __name__ == '__main__':
    unittest.main()
