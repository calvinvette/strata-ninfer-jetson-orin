import struct
import tempfile
import unittest
from pathlib import Path

from compare_gdn_state_dumps import compare


HEADER = struct.Struct('<8sQQQ')


def write_dump(path: Path, layers: list[list[float]]) -> None:
    width = len(layers[0])
    with path.open('wb') as stream:
        stream.write(HEADER.pack(b'STGDN01\0', 17, len(layers), width))
        for layer in layers:
            stream.write(struct.pack(f'<{width}f', *layer))


class GdnStateDumpTest(unittest.TestCase):
    def test_reports_exact_and_numeric_differences(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference, candidate = root / 'ref.bin', root / 'candidate.bin'
            write_dump(reference, [[1.0, 2.0, 3.0], [-1.0, 0.5, 4.0]])
            write_dump(candidate, [[1.0, 2.5, 3.0], [-1.0, 0.5, 2.0]])
            result = compare(reference, candidate)
        self.assertEqual(result['different_floats'], 2)
        self.assertAlmostEqual(result['fraction_different'], 1 / 3)
        self.assertAlmostEqual(result['global_rms_abs_delta'], (4.25 / 6) ** 0.5)
        self.assertEqual(result['max_element_error'], {'layer': 1, 'index': 2, 'max_abs': 2.0})
        self.assertAlmostEqual(result['per_layer'][0]['relative_l2'], 0.5 / 14 ** 0.5)

    def test_rejects_mismatched_or_truncated_dumps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / 'a.bin', root / 'b.bin'
            write_dump(a, [[1.0, 2.0]])
            write_dump(b, [[1.0, 2.0, 3.0]])
            with self.assertRaisesRegex(ValueError, 'shapes differ'):
                compare(a, b)
            b.write_bytes(b'broken')
            with self.assertRaisesRegex(ValueError, 'truncated'):
                compare(a, b)


if __name__ == '__main__':
    unittest.main()
