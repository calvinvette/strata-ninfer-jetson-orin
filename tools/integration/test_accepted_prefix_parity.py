import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import args_for, parse_hashes


class AcceptedPrefixParityTests(unittest.TestCase):
    def test_embedded_commit_fingerprints_do_not_count_as_final_fingerprints(self):
        line = ('L=12 gdn=a1 ple=b2 tail=c3 dead=d4 pooled=e5 pooled_full=f6 '
                'kv=a7 ple_prev=12,34')
        with __import__('tempfile').TemporaryDirectory() as directory:
            log = Path(directory) / 'engine.log'
            log.write_text(
                f'strata serve: ACCEPTED_PREFIX position=11 committed=1 state={{STATE_HASH {line}}}\n'
                f'strata serve: STATE_HASH {line}\n', encoding='utf-8')
            self.assertEqual(parse_hashes(log), [{
                'L': '12', 'gdn': 'a1', 'ple': 'b2', 'tail': 'c3', 'dead': 'd4',
                'pooled': 'e5', 'pooled_full': 'f6', 'kv': 'a7', 'ple_prev': '12,34',
            }])

    def test_mtp_off_removes_draft_weights_and_uses_native_minimum_spec(self):
        cfg = {'args': ['--native', 'model.gguf', '--mtp', 'mtp/rt', '--spec', '4', '--mtp-max-t', '4']}
        args = args_for(cfg, 0)
        self.assertNotIn('--mtp', args)
        self.assertNotIn('--mtp-max-t', args)
        self.assertEqual(args[args.index('--spec') + 1], '2')

    def test_mtp_window_sets_spec_and_drafter_window(self):
        cfg = {'args': ['--native', 'model.gguf', '--mtp', 'mtp/rt', '--spec', '4']}
        args = args_for(cfg, 3)
        self.assertIn('--mtp', args)
        self.assertEqual(args[args.index('--spec') + 1], '3')
        self.assertEqual(args[args.index('--mtp-max-t') + 1], '3')

    def test_config_adaptive_swap_policy_can_be_preserved(self):
        cfg = {'args': ['--adapt-every', '4', '--adapt-accepted-only',
                        '--mtp', 'mtp/rt', '--spec', '4']}
        args = args_for(cfg, 3, disable_adaptive_swaps=False)
        self.assertNotIn('--adapt-swaps', args)
        self.assertIn('--adapt-accepted-only', args)
        self.assertEqual(args[args.index('--adapt-every') + 1], '4')

    def test_default_adaptive_swap_policy_is_disabled(self):
        args = args_for({'args': ['--mtp', 'mtp/rt']}, 2)
        self.assertEqual(args[args.index('--adapt-swaps') + 1], '0')

    def test_kv_format_override_preserves_mtp_arms(self):
        cfg = {'args': ['--native', 'model.gguf', '--mtp', 'mtp/rt', '--spec', '4', '--kv', 'fp16']}
        for spec in (0, 2, 3, 4):
            args = args_for(cfg, spec, 'int8')
            self.assertEqual(args[args.index('--kv') + 1], 'int8')
            self.assertEqual(args[args.index('--spec') + 1], str(max(2, spec)))
            self.assertEqual('--mtp' in args, spec != 0)


if __name__ == '__main__':
    unittest.main()
