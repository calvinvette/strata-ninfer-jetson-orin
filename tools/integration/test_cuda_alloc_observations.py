import json
import unittest

from cuda_alloc_observations import PREFIX, summarize


def event(pid, op, size, current, high, status=0):
    return PREFIX + json.dumps({
        'pid': pid, 'op': op, 'ptr': '0x1000', 'bytes': size,
        'status': status, 'current_bytes': current, 'high_bytes': high,
    })


class CudaAllocationObservationTests(unittest.TestCase):
    def test_separates_process_ledgers_and_retains_current_and_peak(self):
        result = summarize([
            'ordinary output',
            event(101, 'malloc', 64, 64, 64),
            event(202, 'malloc', 128, 128, 128),
            event(101, 'free', 64, 0, 64),
            event(202, 'malloc', 256, 384, 384),
        ], {101: 'vision encoder'})
        self.assertEqual([p['pid'] for p in result['processes']], [101, 202])
        self.assertEqual(result['processes'][0]['last_current_bytes'], 0)
        self.assertEqual(result['processes'][0]['cuda_runtime_highwater_bytes'], 64)
        self.assertEqual(result['processes'][0]['label'], 'vision encoder')
        self.assertEqual(result['processes'][1]['allocation_events'], 2)
        self.assertEqual(result['processes'][1]['last_current_bytes'], 384)
        self.assertIn('not physical backing', result['scope'])

    def test_failed_runtime_calls_are_counted_without_inventing_success(self):
        result = summarize([event(101, 'malloc', 4096, 0, 0, status=2)])
        process = result['processes'][0]
        self.assertEqual(process['allocation_events'], 1)
        self.assertEqual(process['failed_events'], 1)
        self.assertEqual(process['cuda_runtime_highwater_bytes'], 0)

    def test_rejects_regressing_interposer_highwater(self):
        with self.assertRaisesRegex(ValueError, 'high-water mark regressed'):
            summarize([event(101, 'malloc', 64, 64, 64),
                       event(101, 'free', 64, 0, 32)])

    def test_rejects_logs_without_interposer_records(self):
        with self.assertRaisesRegex(ValueError, 'no CUDA_ALLOC_PROBE records'):
            summarize(['CUDA runtime initialized'])


if __name__ == '__main__':
    unittest.main()
