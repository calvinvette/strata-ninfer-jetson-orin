import unittest
import xml.etree.ElementTree as ET

from plot_e6_same_map_backend import METRICS, SERIES, collect, svg_chart


def base_evidence():
    evidence = {}
    for label, _, root_key, metric_path, point_key, interval_key in SERIES:
        root = evidence
        for key in root_key.split('.'):
            root = root.setdefault(key, {})
        for key in metric_path.split('.'):
            root = root.setdefault(key, {})
        for name, _, _ in METRICS:
            key = {'ttft': 'ttft_s', 'client': 'client_s'}.get(name, name)
            root[key] = {point_key: 0.0, interval_key: [-1.0, 1.0]}
    return evidence


def paired_evidence():
    return {
        'paired_summary': {
            key: {
                'median_within_block_candidate_over_baseline': 1.0,
                'paired_bootstrap_95_interval': [0.99, 1.01],
            }
            for key in ('decode_tps', 'prompt_tps', 'client_ttft_s', 'client_total_s')
        }
    }


class SameMapChartTests(unittest.TestCase):
    def test_ledger_capacity_cells_are_ordered_and_svg_is_valid(self):
        paired = paired_evidence()
        rows = collect(
            base_evidence(),
            paired,
            paired,
            paired,
            paired,
            paired,
            paired,
        )
        labels = [row['label'] for row in rows]
        self.assertEqual(labels[:7], [
            '2K retrieval', '2K code', 'L@4K', 'L@8K',
            'L@16K', 'L@32K', '8K code',
        ])
        rendered = svg_chart(rows)
        root = ET.fromstring(rendered)
        texts = [node.text for node in root.iter() if node.tag.endswith('text')]
        self.assertEqual(len(rows), 14)
        self.assertTrue(any(text == 'L@32K' for text in texts))


if __name__ == '__main__':
    unittest.main()
