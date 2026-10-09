import json
from pathlib import Path
import tempfile
import unittest

from summarize_controls import summarize


class PairedSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        runs = []
        baseline = [10, 20, 100]
        candidate = [11, 44, 110]
        for block in range(3):
            for variant, rates in [('baseline', baseline), ('candidate', candidate)]:
                directory = self.root / f'block-{block}-{variant}'
                directory.mkdir()
                runs.append({'block': block, 'variant': variant, 'status': 'pass'})
                config = {'args': ['--expert-cache', '5000'], 'tokenizer': '/explicit/tokenizer', 'env': {}}
                (directory / 'server-config.json').write_text(json.dumps(config))
                counter = {'prompt_tokens': 512, 'prompt_read': 512, 'output_tokens': 64, 'engine_generated': 64,
                           'prompt_ms': 512000 / rates[block], 'decode_ms': 6400, 'reused': 0}
                row = {'cell': 'pp512+tg64', 'warmup': False, 'status': 'pass',
                       'request_start_monotonic_s': 1, 'request_end_monotonic_s': 3, 'client_elapsed_s': 2,
                       'stream_observation': {'first_visible_delta_s': 1},
                       'response': {'usage': {'prompt_tokens': 512, 'completion_tokens': 64},
                                    'choices': [{'message': {'content': 'same'}}]},
                       'metrics_after': {'requests': [counter], 'engine': {'expert_slots': 6519, 'expert_cache_mib': 12695}}}
                (directory / 'requests.json').write_text(json.dumps({'checks': [row]}))
                (directory / 'memory.jsonl').write_text(json.dumps({'monotonic_s': 2, 'available_bytes': 7 * 1024**3, 'swap_used_bytes': 0}) + '\n')
        (self.root / 'campaign.json').write_text(json.dumps({'runs': runs, 'planned_blocks': 3}))

    def test_pair_estimator_is_not_ratio_of_displayed_medians(self):
        result = summarize(self.root)['cells'][0]['prompt_tps']
        self.assertAlmostEqual(result['median_within_block_candidate_over_baseline'], 1.1)
        self.assertAlmostEqual(result['candidate_median'] / result['baseline_median'], 2.2)

    def test_actual_resource_mismatch_rejected(self):
        path = self.root / 'block-1-candidate/requests.json'
        data = json.loads(path.read_text())
        data['checks'][0]['metrics_after']['engine']['expert_slots'] = 6000
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'resource/workload mismatch'):
            summarize(self.root)

    def test_unpaired_failed_block_retained_and_excluded(self):
        path = self.root / 'campaign.json'
        data = json.loads(path.read_text())
        data['runs'][1].update(status='pressure_abort', reason='physical headroom')
        path.write_text(json.dumps(data))
        result = summarize(self.root)
        self.assertEqual(result['cells'][0]['paired_blocks'], 2)
        self.assertEqual(result['rejected_or_incomplete'][0]['status'], 'pressure_abort')

    def test_clock_gap_is_explicit(self):
        result = summarize(self.root)
        observed = result['raw_paired_blocks']['pp512+tg64'][0]['baseline']['gpu_observed_hz']
        self.assertEqual(observed, {'samples': 0, 'minimum': None, 'maximum': None})
