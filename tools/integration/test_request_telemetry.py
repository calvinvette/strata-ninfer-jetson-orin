import unittest

from request_telemetry import window_energy


class RailIntegrationTests(unittest.TestCase):
    def test_constant_power_and_clipped_window(self):
        points = [{'wall_time_s': t, 'rails_watts': {'rail': 2}} for t in range(5)]
        energy = window_energy(points, 0.5, 3.5)
        self.assertEqual(energy['joules_by_named_rail']['rail'], 6)

    def test_linear_power_is_integrated_without_summing_rails(self):
        points = [{'wall_time_s': 0, 'rails_watts': {'a': 0, 'b': 10}},
                  {'wall_time_s': 2, 'rails_watts': {'a': 4, 'b': 10}}]
        result = window_energy(points, 0.5, 1.5)
        self.assertEqual(result['joules_by_named_rail'], {'a': 2, 'b': 10})

    def test_missing_endpoint_or_long_gap_is_not_filled(self):
        points = [{'wall_time_s': 0, 'rails_watts': {'rail': 2}},
                  {'wall_time_s': 5, 'rails_watts': {'rail': 2}}]
        self.assertEqual(window_energy(points, 1, 4)['status'], 'unsupported')
        self.assertEqual(window_energy(points, -1, 4)['status'], 'unsupported')
