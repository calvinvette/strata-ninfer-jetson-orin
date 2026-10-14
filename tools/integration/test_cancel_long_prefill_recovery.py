import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from cancel_long_prefill_recovery import STATE_KEYS, canceled_prefill_line, final_state


class FinalStateTests(unittest.TestCase):
    def test_reads_last_complete_fingerprint(self):
        first = ' '.join(f'{key}={index:x}' for index, key in enumerate(STATE_KEYS))
        last = ' '.join(f'{key}={index + 1:x}' for index, key in enumerate(STATE_KEYS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'engine.log'
            path.write_text(f'strata serve: STATE_HASH L=1 {first}\n'
                            f'strata serve: STATE_HASH L=2 {last}\n')
            self.assertEqual(final_state(path), dict(
                (key, f'{index + 1:x}') for index, key in enumerate(STATE_KEYS)))

    def test_rejects_missing_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'engine.log'
            path.write_text('strata serve: ready\n')
            with self.assertRaisesRegex(RuntimeError, 'no complete persistent-state'):
                final_state(path)

    def test_parses_engine_cancellation_and_read_count(self):
        line = ('strata serve: prompt 8192 tokens = 0 reused + 1024 of 8192 read in '
                '19437 ms (52.7 tok/s), 0 generated in 0 ms (0.0 tok/s), '
                'drafts accepted 0 of 0, 0 checkpoints (cancelled)')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'engine.log'
            path.write_text(line + '\n')
            record = canceled_prefill_line(path)
        self.assertEqual(record['generated_tokens'], 0)
        self.assertEqual(record['read_tokens'], 1024)
        self.assertEqual(record['prompt_tokens'], 8192)

    def test_rejects_successful_completion_as_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'engine.log'
            path.write_text('strata serve: prompt 20 tokens = 20 read, 5 generated in 1 ms\n')
            self.assertIsNone(canceled_prefill_line(path))


if __name__ == '__main__':
    unittest.main()
