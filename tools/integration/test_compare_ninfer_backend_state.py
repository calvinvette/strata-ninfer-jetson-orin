import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_ninfer_backend_state import compare, read_arm


def log_text(tokens, *, changed=False):
    fields = ('L=3 gdn=0000000000000001 ple=0000000000000002 '
              'tail=0000000000000003 dead=0000000000000004 '
              'pooled=0000000000000005 pooled_full=0000000000000006 '
              'kv=0000000000000007 mtp=0000000000000008 stale=0000000000000009 '
              'ple_prev=1,2')
    if changed:
        fields = fields.replace('gdn=0000000000000001', 'gdn=00000000000000ff')
    line = (f'strata serve: ACCEPTED_PREFIX position=2 window=1 accepted_drafts=0 '
            f'committed=1 tokens={tokens} state={{STATE_HASH {fields}}}')
    final = f'strata serve: STATE_HASH {fields}'
    return line + '\n' + final + '\n'


class CompareNinferBackendStateTests(unittest.TestCase):
    def test_equal_tokens_and_state_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            strata, ninfer = Path(tmp) / 'strata.log', Path(tmp) / 'ninfer.log'
            strata.write_text(log_text(42))
            ninfer.write_text(log_text(42))
            result = compare(strata, ninfer)
            self.assertTrue(result['passed'])
            self.assertEqual(result['strata_generated_tokens'], [42])
            self.assertTrue(result['common_prefixes'][0]['equal'])

    def test_detect_token_and_prefix_state_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            strata, ninfer = Path(tmp) / 'strata.log', Path(tmp) / 'ninfer.log'
            strata.write_text(log_text(42))
            ninfer.write_text(log_text(43, changed=True))
            result = compare(strata, ninfer)
            self.assertFalse(result['passed'])
            self.assertFalse(result['token_ids_equal'])
            self.assertEqual(result['common_prefixes'][0]['differing_fields'], ['gdn'])
            self.assertIn('gdn', result['final_state_differing_fields'])

    def test_missing_accepted_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'empty.log'
            path.write_text('strata serve: STATE_HASH L=3\n')
            with self.assertRaisesRegex(ValueError, 'no accepted-prefix'):
                read_arm(path)


if __name__ == '__main__':
    unittest.main()
