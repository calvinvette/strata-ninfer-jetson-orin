import struct
import tempfile
import unittest
from pathlib import Path

from compare_prefill_gdn_state import compare


HEADER = struct.Struct('<8sIiqQQi4x')


def write_capture(path: Path, layer: int, boundary: int, values: list[float]) -> None:
    recurrent = 1
    with path.open('wb') as stream:
        stream.write(HEADER.pack(b'STPFGS1\0', 1, layer, boundary,
                                 recurrent, len(values), boundary))
        stream.write(struct.pack(f'<{len(values)}f', *values))


class PrefillGdnStateComparisonTests(unittest.TestCase):
    def test_compares_prefill_state_and_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference, candidate = root / 'ref.bin', root / 'candidate.bin'
            write_capture(reference, 4, 2041, [1.0, 2.0, -3.0])
            write_capture(candidate, 4, 2041, [1.0, 2.5, -3.0])
            result = compare(reference, candidate)
        row = result['records'][0]
        self.assertEqual(result['first_differing_layer'], 4)
        self.assertEqual(row['different_values'], 1)
        self.assertAlmostEqual(row['relative_l2'], 0.5 / (14.0 ** 0.5))
        self.assertEqual(row['max_abs_delta'], 0.5)

    def test_rejects_mismatched_prompt_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference, candidate = root / 'ref.bin', root / 'candidate.bin'
            write_capture(reference, 4, 2041, [1.0])
            write_capture(candidate, 4, 2040, [1.0])
            with self.assertRaisesRegex(ValueError, 'records differ'):
                compare(reference, candidate)


if __name__ == '__main__':
    unittest.main()
