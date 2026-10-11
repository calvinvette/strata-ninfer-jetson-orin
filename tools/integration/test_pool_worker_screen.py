"""Unit checks for the randomized CPU worker screen helpers."""
import json
import tempfile
import unittest
from pathlib import Path

from pool_worker_screen import exact_warmup_prompt, paired_deltas, read_state_hashes, set_arg


class PoolWorkerScreenTests(unittest.TestCase):
    def test_set_arg_replaces_or_appends_once(self):
        args = ['--pool-workers', '11']
        set_arg(args, '--pool-workers', 4)
        set_arg(args, '--prompt-cache', 6)
        self.assertEqual(args, ['--pool-workers', '4', '--prompt-cache', '6'])

    def test_distinct_warmup_prompt_can_hit_requested_token_count(self):
        encode = lambda text: text.split()
        prompt = exact_warmup_prompt(32, encode)
        self.assertEqual(len(encode(prompt)), 32)
        self.assertIn('blue', prompt)
        self.assertNotIn('red', prompt)

    def test_state_hash_parser_requires_complete_record(self):
        keys = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
        fields = dict(zip(keys, ('519', 'a', 'b', 'c', 'd', 'e', 'f', '0', '1,2')))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'engine.log'
            path.write_text('strata: STATE_HASH ' + ' '.join(f'{k}={v}' for k, v in fields.items()) + '\n')
            self.assertEqual(read_state_hashes(path), [fields])
            path.write_text('strata: STATE_HASH L=519 gdn=a\n')
            with self.assertRaises(ValueError):
                read_state_hashes(path)

    def test_paired_deltas_resample_independent_process_blocks(self):
        rows = [
            dict(workers=11, repetition=0, request_ms=100),
            dict(workers=4, repetition=0, request_ms=90),
            dict(workers=11, repetition=1, request_ms=200),
            dict(workers=4, repetition=1, request_ms=180),
        ]
        self.assertEqual(paired_deltas(rows, 11), {'4': [-10.0, -10.0]})


if __name__ == '__main__':
    unittest.main()
