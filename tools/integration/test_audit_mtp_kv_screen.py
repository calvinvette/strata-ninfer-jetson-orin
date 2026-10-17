import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from audit_mtp_kv_screen import audit


def sample_campaign():
    runs = []
    for block in range(2):
        for kv in ('fp16', 'int8'):
            for workload in ('short', 'long'):
                for window in (0, 4):
                    slots = 3903
                    if block == 0 and (kv, workload, window) == ('fp16', 'short', 0):
                        slots = 3803
                    runs.append({
                        'block': block, 'kv': kv, 'workload': workload,
                        'window': window, 'status': 'pass', 'local_run_date': '2026-10-16',
                        'engine': {'kv': kv, 'expert_slots': slots, 'expert_cache_mib': 7615},
                        'metrics': {'prompt_tokens': 512 if workload == 'short' else 7501,
                                    'prompt_tps': 10 + window, 'decode_tps': 20 + window,
                                    'client_ttft_s': 3 - window / 10,
                                    'client_total_s': 5 - window / 10},
                    })
    return {'source_commit': 'abc', 'seed': 1, 'mtp_windows': [0, 4],
            'kv_formats': ['fp16', 'int8'], 'workloads': ['short', 'long'], 'runs': runs}


class AuditMtpKvScreenTests(unittest.TestCase):
    def test_mismatched_residency_excluded_and_higher_interactions_require_all_cells(self):
        result = audit(sample_campaign())
        self.assertEqual(len(result['excluded_cell_pairs']), 1)
        self.assertEqual(result['excluded_cell_pairs'][0]['reason'].split()[0], 'residency')
        fp_short = next(x for x in result['cell_effects'] if x['kv'] == 'fp16' and x['workload'] == 'short')
        self.assertEqual(fp_short['paired_blocks'], 1)
        self.assertEqual(fp_short['paired_block_ids'], [1])
        self.assertFalse(next(x for x in result['three_way_interactions'] if x['block'] == 0)['qualified'])
        self.assertTrue(next(x for x in result['three_way_interactions'] if x['block'] == 1)['qualified'])

    def test_qualified_pair_preserves_metrics_and_actual_residency(self):
        result = audit(sample_campaign())
        pair = next(x for x in result['qualified_cell_pairs']
                    if x['block'] == 1 and x['kv'] == 'int8' and x['workload'] == 'long')
        self.assertEqual(pair['expert_slots'], 3903)
        self.assertAlmostEqual(pair['decode_tps_ratio'], 24 / 20)

    def test_cross_day_pair_is_not_timing_qualified(self):
        campaign = sample_campaign()
        next(row for row in campaign['runs']
             if row['block'] == 1 and row['kv'] == 'int8' and
             row['workload'] == 'short' and row['window'] == 4)['local_run_date'] = '2026-10-17'
        result = audit(campaign)
        exclusion = next(x for x in result['excluded_cell_pairs']
                         if x['block'] == 1 and x['kv'] == 'int8' and x['workload'] == 'short')
        self.assertIn('same-local-day', exclusion['reason'])


if __name__ == '__main__':
    unittest.main()
