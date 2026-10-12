import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from mtp_cancel_state_parity import (STATE_KEYS, compare_prefix_traces,
                                    parse_prefix_entries, state_dump_env)
from serve.server import StrataEngine


class MtpCancelStateParityTests(unittest.TestCase):
    def test_ignore_eos_request_key_is_opt_in(self):
        self.assertNotIn('ignore_eos=', StrataEngine.sampling_keys({}))
        self.assertIn('ignore_eos=1', StrataEngine.sampling_keys(
            {'strata_tune': {'ignore_eos': True}}))
        self.assertNotIn('ignore_eos=', StrataEngine.sampling_keys(
            {'strata_tune': {'ignore_eos': False}}))

    def _entry(self, length, tokens):
        return {'position': length - 1, 'window': 2, 'accepted_drafts': len(tokens) - 1,
                'committed': len(tokens), 'token_ids': tokens,
                'state': {key: str(length) if key == 'L' else f'{key}-hash'
                          for key in STATE_KEYS}}

    def test_parses_full_accepted_prefix_fingerprint(self):
        fields = 'L=512 ' + ' '.join(
            f'{key}={index:016x}' for index, key in enumerate(STATE_KEYS) if key != 'L')
        line = ('strata serve: ACCEPTED_PREFIX position=511 window=2 accepted_drafts=1 '
                f'committed=2 tokens=42,43 state={{STATE_HASH {fields}}}')
        parsed = parse_prefix_entries([line])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['token_ids'], [42, 43])
        self.assertEqual(parsed[0]['state']['L'], '512')
        self.assertEqual(set(parsed[0]['state']), set(STATE_KEYS))

    def test_compares_every_shared_boundary_and_rejects_divergent_state(self):
        cancel = [self._entry(512, [42, 43]), self._entry(514, [44])]
        reference = [self._entry(512, [42, 43]), self._entry(514, [44])]
        result = compare_prefix_traces(cancel, reference)
        self.assertTrue(result['passed'])
        self.assertEqual(result['shared_state_lengths'], ['512', '514'])
        reference[1]['state']['gdn'] = 'different'
        self.assertFalse(compare_prefix_traces(cancel, reference)['passed'])

    def test_rejects_missing_reference_boundary_and_token_mismatch(self):
        cancel = [self._entry(512, [42]), self._entry(513, [43])]
        reference = [self._entry(512, [42]), self._entry(513, [99])]
        result = compare_prefix_traces(cancel, reference)
        self.assertFalse(result['passed'])
        self.assertIn('committed token IDs differ', result['failures'])

    def test_gdn_dump_environment_is_opt_in_and_does_not_mutate_base(self):
        base = {'STRATA_STATE_HASH': '1'}
        self.assertEqual(state_dump_env(base, '/tmp/state.bin', None), base)
        configured = state_dump_env(base, '/tmp/state.bin', 48)
        self.assertEqual(configured['STRATA_STATE_DUMP_GDN_AT'], '48')
        self.assertEqual(configured['STRATA_STATE_HASH'], '1')
        self.assertNotIn('STRATA_STATE_DUMP_GDN_AT', base)


if __name__ == '__main__':
    unittest.main()
