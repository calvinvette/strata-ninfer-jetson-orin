import unittest

from benchmark_control import qualify, request, stream_request


class WorkloadQualificationTests(unittest.TestCase):
    def setUp(self):
        self.cell = {'prompt_tokens': 512, 'generate_tokens': 64}
        self.row = {'response': {'usage': {'prompt_tokens': 512, 'completion_tokens': 64},
                                 'timings': {'cache_n': 0, 'prompt_per_second': 50.0,
                                             'predicted_per_second': 20.0}}}

    def test_completed_workload(self):
        self.assertEqual(qualify(self.row, self.cell)[0], 'pass')

    def test_early_stop_is_failed_cell(self):
        self.row['response']['usage']['completion_tokens'] = 2
        self.assertEqual(qualify(self.row, self.cell)[0], 'fail')

    def test_template_mismatch_is_failed_cell(self):
        self.row['response']['usage']['prompt_tokens'] = 511
        self.assertEqual(qualify(self.row, self.cell)[0], 'fail')

    def test_reused_prompt_is_not_a_fresh_prefill_control(self):
        self.row['response']['timings']['cache_n'] = 100
        self.assertEqual(qualify(self.row, self.cell)[0], 'fail')

    def test_missing_timings_is_failed_cell(self):
        del self.row['response']['timings']
        self.assertEqual(qualify(self.row, self.cell)[0], 'fail')

    def test_nonfinite_rates_are_failed_cells(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value):
                self.row['response']['timings']['prompt_per_second'] = value
                self.assertEqual(qualify(self.row, self.cell)[0], 'fail')

    def test_readiness_can_bound_a_stalled_http_read(self):
        import io
        from unittest.mock import patch
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{}')) as urlopen:
            self.assertEqual(request('http://127.0.0.1:18081', '/health', timeout=5), {})
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 5)

    def test_stream_role_only_is_not_first_visible_delta(self):
        import io
        import json
        from unittest.mock import patch
        events = [{'choices': [{'delta': {'role': 'assistant'}}]},
                  {'choices': [{'delta': {'content': 'one two'}}]},
                  {'usage': {'prompt_tokens': 512, 'completion_tokens': 64},
                   'timings': {'cache_n': 0}}]
        wire = b''.join(b'data: ' + json.dumps(x).encode() + b'\n\n' for x in events)
        wire += b'data: [DONE]\n\n'
        with patch('urllib.request.urlopen', return_value=io.BytesIO(wire)), \
             patch('time.monotonic', side_effect=[100, 101, 102, 103]):
            response, observation = stream_request('http://127.0.0.1:18081', {})
        self.assertEqual(observation['first_visible_delta_s'], 2)
        self.assertEqual(response['choices'][0]['message']['content'], 'one two')
        self.assertEqual(response['usage']['completion_tokens'], 64)
        self.assertEqual(len(observation['events']), 3)
