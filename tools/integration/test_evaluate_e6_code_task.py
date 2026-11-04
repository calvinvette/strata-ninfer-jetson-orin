#!/usr/bin/env python3
"""Regression tests for the bounded E6 generated-code quality oracle."""
import unittest

from evaluate_e6_code_task import compile_solution, evaluate


SOLUTION = '''```python
def merge_ranges(ranges):
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda pair: pair[0])
    merged = []
    for start, end in ordered:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```'''


class EvaluateCodeTaskTests(unittest.TestCase):
    def test_fenced_model_solution_passes_behavior_and_immutability(self):
        result = evaluate(SOLUTION)
        self.assertTrue(result['passed'])
        self.assertEqual(result['unit_cases'], 5)
        self.assertTrue(result['input_immutability'])

    def test_wrong_behavior_fails_oracle(self):
        code = 'def merge_ranges(ranges):\n    return ranges\n'
        with self.assertRaises(AssertionError):
            evaluate(code)

    def test_imports_are_rejected(self):
        code = 'def merge_ranges(ranges):\n    import os\n    return []\n'
        with self.assertRaisesRegex(ValueError, 'unsupported syntax: Import'):
            compile_solution(code)

    def test_unapproved_builtin_is_rejected(self):
        code = 'def merge_ranges(ranges):\n    return open("/tmp/x")\n'
        with self.assertRaisesRegex(ValueError, 'unsupported function call: open'):
            compile_solution(code)

    def test_unexpected_top_level_statement_is_rejected(self):
        code = 'def merge_ranges(ranges):\n    return []\nprint("extra")\n'
        with self.assertRaisesRegex(ValueError, 'define only merge_ranges'):
            compile_solution(code)


if __name__ == '__main__':
    unittest.main()
