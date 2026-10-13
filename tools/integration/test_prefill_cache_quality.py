"""Offline tests for the full-task cache × prefill quality rubric."""
import unittest

from prefill_cache_quality import rubric


class PrefillCacheQualityTest(unittest.TestCase):
    def test_accepts_complete_task_and_counts_words(self):
        text = ('Processor: ' + 'A computer fetches instructions, decodes them, and executes '
                'them. RAM stores binary data from input and prepares output. ' * 45 +
                '17 x 19 = 323')
        checks, words = rubric(text)
        self.assertEqual(words, len(text.split()))
        self.assertTrue(all(checks.values()))

    def test_rejects_missing_arithmetic_and_short_answer(self):
        checks, words = rubric('Processor: fetch decode execute RAM binary input output')
        self.assertLess(words, 200)
        self.assertFalse(checks['at_least_200_words'])
        self.assertFalse(checks['exact_arithmetic'])

    def test_task_specific_computer_explanation_rubric(self):
        accepted, count = rubric('Processor: ' + 'Computer information. ' * 100,
                                 'computer-explanation')
        rejected, _ = rubric('A processor handles information. ' * 100,
                             'computer-explanation')
        self.assertEqual(count, 201)
        self.assertTrue(all(accepted.values()))
        self.assertFalse(rejected['starts_with_processor'])


if __name__ == '__main__':
    unittest.main()
