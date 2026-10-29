import xml.etree.ElementTree as ET
import unittest

from plot_ninfer_api_effects import METRICS, render


class NoStagingApiPlotTests(unittest.TestCase):
    def test_render_contains_all_pair_points_and_parses_as_svg(self):
        cells = []
        for name in ('pp512+tg64', 'pp2048+tg128'):
            metrics = {}
            for index, (key, _, _) in enumerate(METRICS):
                metrics[key] = {
                    'median_paired_change_pct': float(index),
                    'bootstrap_95_interval_pct': [-1.0, 2.0],
                    'paired_changes_pct': [
                        {'block': block, 'order': 'Strata → NInfer', 'value': block + index}
                        for block in range(3)
                    ],
                }
            cells.append({'name': name, 'metrics': metrics})

        document = render({'cells': cells})
        root = ET.fromstring(document)
        namespace = {'svg': 'http://www.w3.org/2000/svg'}

        self.assertTrue(root.tag.endswith('svg'))
        self.assertEqual(len(root.findall('.//svg:circle', namespace)), 24)
        self.assertEqual(len(root.findall('.//svg:path', namespace)), 8)
        self.assertIn('bootstrap 95%', document)
        self.assertIn('pp2048+tg128', document)


if __name__ == '__main__':
    unittest.main()
