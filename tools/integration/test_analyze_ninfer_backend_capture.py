#!/usr/bin/env python3
"""Unit checks for single- and multi-position NInfer capture analysis."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest

from analyze_ninfer_backend_capture import analyze_layer


INPUT = struct.Struct('<8sIIIIQq8i')
ROW = struct.Struct('<8sIIIIQqii')


def write_capture(root: Path, arm: str, position: int, changed: bool) -> None:
    layer_dir = root / 'run-layer3'
    layer_dir.mkdir(parents=True, exist_ok=True)
    token = 123 + position
    route = {'layer': 3, 'position': position, 'token_id': token,
             'ids': list(range(10)), 'weights': [0.1] * 10}
    route_path = layer_dir / f'{arm}.layer3.route'
    with route_path.open('a') as stream:
        if stream.tell() == 0:
            stream.write(json.dumps({'format': 'strata-verify-moe-route-v1', 'k': 10}) + '\n')
        stream.write(json.dumps(route) + '\n')
    delta = 1.0 if changed and position == 128 else 0.0
    values = [delta] + [0.0] * 2559
    with (layer_dir / f'{arm}.layer3.input').open('ab') as stream:
        stream.write(INPUT.pack(b'STMOINP1', 1, 3, 1, 0, 2560, position,
                                token, 0, 0, 0, 0, 0, 0, 0))
        stream.write(struct.pack('<2560f', *values))
    with (layer_dir / f'{arm}.layer3.parts').open('ab') as stream:
        stream.write(ROW.pack(b'STMPART2', 2, 3, 10, 0, 2560, position, -1, token))
        parts = [0.0] * 25600
        if changed and position == 128:
            parts[4 * 2560] = 2.0
        stream.write(struct.pack('<25600f', *parts))
    with (layer_dir / f'{arm}.layer3.output').open('ab') as stream:
        stream.write(ROW.pack(b'MOEOUT02', 2, 3, 1, 0, 2560, position, -1, token))
        stream.write(struct.pack('<5120f', *([0.0] * 5120)))


class CaptureAnalysisTests(unittest.TestCase):
    def test_multiple_positions_are_aligned_and_compared_independently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for arm in ('strata-control', 'ninfer-control'):
                for position in (0, 128):
                    write_capture(root, arm, position,
                                  changed=arm == 'ninfer-control')
            rows = analyze_layer(root, 3, 'strata-control', 'ninfer-control')['positions']
            self.assertEqual([row['position'] for row in rows], [0, 128])
            self.assertEqual(rows[0]['input']['different'], 0)
            self.assertEqual(rows[1]['input']['different'], 1)
            self.assertEqual(rows[1]['expert_parts']['different'], 1)
            self.assertEqual(rows[1]['per_expert_parts'][4]['expert_id'], 4)
            self.assertEqual(rows[1]['per_expert_parts'][4]['different'], 1)
            self.assertEqual(rows[1]['per_expert_parts'][3]['different'], 0)


if __name__ == '__main__':
    unittest.main()
