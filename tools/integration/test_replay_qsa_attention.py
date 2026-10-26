#!/usr/bin/env python3
import struct
import tempfile
import unittest
from array import array
from pathlib import Path

from compare_qsa_capture import HEADER as QSA_HEADER
from compare_qsa_kv_capture import HEADER as KV_HEADER
from replay_qsa_attention import fwht256, replay


def write_fixture(qsa_path, kv_path):
    qsa_head_dim = 256
    qsa_input = [0.0]
    query = [0.0] * qsa_head_dim
    index_query = [0.0]
    current_key = [0.0] * qsa_head_dim
    current_value = [0.0] * qsa_head_dim
    selection = [0]
    attention = [float(i) / 256.0 for i in range(qsa_head_dim)]
    gated = [0.0] * qsa_head_dim
    projected = [0.0]
    moe_input = [0.0]
    qsa_header = QSA_HEADER.pack(b"STQSAD1", 1, 3, 0, 1, qsa_head_dim, 1, qsa_head_dim, 1, 7, 0)
    qsa_payload = array("f", qsa_input + query + index_query + current_key + current_value +
                        selection + attention + gated + projected + moe_input)
    qsa_path.write_bytes(qsa_header + qsa_payload.tobytes())
    kv_header = KV_HEADER.pack(b"STQKVD1", 1, 3, 0, 1, qsa_head_dim, 1, 7, 1)
    kv_payload = array("f", [0.0] * qsa_head_dim + attention)
    kv_path.write_bytes(kv_header + kv_payload.tobytes())


class ReplayQsaAttentionTests(unittest.TestCase):
    def test_one_selected_cell_replays_value_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qsa, kv = root / "capture.qsa", root / "capture.kv"
            write_fixture(qsa, kv)
            result = replay(qsa, kv)
            self.assertEqual(result["reference_vs_engine_attention"]["different"], 0)

    def test_fwht_is_self_inverse(self):
        source = [float(i % 13 - 6) for i in range(256)]
        restored = fwht256(fwht256(source))
        self.assertLess(max(abs(a - b) for a, b in zip(source, restored)), 1e-12)


if __name__ == "__main__":
    unittest.main()
