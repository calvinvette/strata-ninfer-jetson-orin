#!/usr/bin/env python3
"""Small binary-format and math tests for gdn_trace_oracle.py."""
from pathlib import Path
import struct
import tempfile
import unittest

import gdn_trace_oracle as oracle


class GdnTraceOracleTests(unittest.TestCase):
    def test_replay_captured_one_step_with_shared_key_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state.bin"
            diag_path = root / "diag.bin"
            raw_o_path = root / "raw-o.bin"

            state = [0.0] * 9  # 2 rows x 2 value heads x 2 columns, plus conv tail
            state_path.write_bytes(oracle.COMMIT_HEADER.pack(
                b"STGCMT1\0", 1, 3, 9, 8, 9, 42, 0) + struct.pack("<9f", *state))

            # [q(2), k(2), v(head0, 2), v(head1, 2)]; both value heads share q/k.
            h = [1.0, 0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
            fields = [
                [0.0, 0.0], h, h, [0.0, 0.0], [0.5, 0.5],
                [0.0] * 4, [0.0] * 4, [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
            ]
            header = oracle.DIAG_HEADER.pack(
                b"STGDIAG4", 4, 3, 1, 10, 2, 8, 2, 4, 8, 7, *([0] * 7))
            diag_path.write_bytes(header + b"".join(struct.pack(f"<{len(x)}f", *x) for x in fields))
            raw_o_path.write_bytes(
                oracle.O_HEADER.pack(b"STGDOO1\0", 1, 3, 1, 10, 4, 7, *([0] * 7))
                + struct.pack("<4f", 0.5, 0.75, 1.0, 1.25))

            result = oracle.run(state_path, diag_path, raw_o_path, 3, 9, 2, 1)
            self.assertEqual(result["positions_replayed"], 1)
            self.assertEqual(result["worst_relative_l2"], 0.0)
            self.assertEqual(result["records"][0]["max_abs"], 0.0)

    def test_rejects_nonconsecutive_captured_positions(self):
        # Position continuity is required because every token updates the same state.
        with self.assertRaisesRegex(ValueError, "consecutive"):
            oracle.validate_positions([10, 12], 9)


if __name__ == "__main__":
    unittest.main()
