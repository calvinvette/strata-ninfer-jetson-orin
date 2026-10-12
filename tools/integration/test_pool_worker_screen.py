"""Unit checks for the randomized CPU worker screen helpers."""
import json
import tempfile
import unittest
from pathlib import Path

from pool_worker_screen import (exact_warmup_prompt, paired_deltas, read_accepted_prefix_trace,
                                worker_transfer_effects,
                                read_state_hashes, set_arg)


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

    def test_accepted_prefix_trace_captures_token_ids_and_all_persistent_fields(self):
        line = ('strata serve: ACCEPTED_PREFIX position=575 window=4 accepted_drafts=2 committed=3 '
                'tokens=12,34,56 state={STATE_HASH L=578 gdn=01 ple=02 tail=03 pooled=04 '
                'kv=05 mtp=06 stale=07 dead=08 pooled_full=09 ple_prev=10,11}\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'engine.log'
            path.write_text(line)
            trace = read_accepted_prefix_trace(path)
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]['token_ids'], [12, 34, 56])
        self.assertEqual(trace[0]['accepted_drafts'], 2)
        self.assertEqual(trace[0]['committed'], 3)
        self.assertEqual(trace[0]['state']['L'], '578')
        self.assertEqual(trace[0]['state']['mtp'], '06')
        self.assertEqual(trace[0]['state']['ple_prev'], '10,11')

    def test_accepted_prefix_trace_selects_last_request_after_warmup(self):
        state = ('STATE_HASH L=512 gdn=01 ple=02 tail=03 pooled=04 kv=05 mtp=06 stale=07 '
                 'dead=08 pooled_full=09 ple_prev=10,11')
        def commit(token):
            return (f'strata serve: ACCEPTED_PREFIX position=511 window=1 accepted_drafts=0 '
                    f'committed=1 tokens={token} state={{{state}}}\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'engine.log'
            path.write_text(commit(12) + f'strata serve: {state}\n' + commit(34) + f'strata serve: {state}\n')
            trace = read_accepted_prefix_trace(path)
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]['token_ids'], [34])

    def test_accepted_prefix_trace_rejects_missing_state_fields(self):
        line = ('strata serve: ACCEPTED_PREFIX position=575 window=4 accepted_drafts=0 committed=1 '
                'tokens=12 state={STATE_HASH L=576 gdn=01}\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'engine.log'
            path.write_text(line)
            with self.assertRaises(ValueError):
                read_accepted_prefix_trace(path)

    def test_paired_deltas_resample_independent_process_blocks(self):
        rows = [
            dict(workers=11, repetition=0, request_ms=100),
            dict(workers=4, repetition=0, request_ms=90),
            dict(workers=11, repetition=1, request_ms=200),
            dict(workers=4, repetition=1, request_ms=180),
        ]
        self.assertEqual(paired_deltas(rows, 11), {'4': [-10.0, -10.0]})

    def test_worker_transfer_effects_pair_within_randomized_blocks(self):
        rows = []
        values = {
            (0, 4, 'mapped'): 100, (0, 4, 'pread'): 120,
            (0, 8, 'mapped'): 90, (0, 8, 'pread'): 99,
            (1, 4, 'mapped'): 200, (1, 4, 'pread'): 240,
            (1, 8, 'mapped'): 180, (1, 8, 'pread'): 198,
        }
        for (rep, workers, mode), request_ms in values.items():
            rows.append({'repetition': rep, 'workers': workers,
                         'transfer_mode': mode, 'request_ms': request_ms})
        effects = worker_transfer_effects(rows, 8, ['mapped', 'pread'])
        for actual, expected in zip(effects['pread_delta_percent_by_workers']['4'], [20.0, 20.0]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(effects['pread_delta_percent_by_workers']['8'], [10.0, 10.0]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(effects['interaction_percentage_points'], [10.0, 10.0]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(effects['worker_delta_percent_by_mode']['mapped']['4'],
                                    [100.0 * (100 / 90 - 1), 100.0 * (200 / 180 - 1)]):
            self.assertAlmostEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
