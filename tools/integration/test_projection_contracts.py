import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from projection_contracts import map_contracts


def matrix(suffix, cols, rows, codec='Q4_K'):
    return {'symbol': 'blk.0.'+suffix, 'shape_fastest_dimension_first': [cols, rows],
            'format': codec, 'ggml_type_id': 12}


class ProjectionContractTests(unittest.TestCase):
    def test_required_profile_rejects_after_preserving_evidence(self):
        inv = {'schema_version': 1, 'tensors': [matrix('attn_qkv.weight',2560,10240),
                                              matrix('attn_gate.weight',2560,6144)]}
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'inventory.json', Path(directory)/'report.json'
            source.write_text(json.dumps(inv))
            command = [sys.executable, str(Path(__file__).with_name('projection_contracts.py')),
                       '--inventory', str(source), '--output', str(output), '--require-direct-profile']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            recorded = output.read_bytes()
            self.assertEqual(json.loads(recorded)['layers'][0]['decision'], 'incompatible_direct_reuse')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), recorded)

    def test_real_gdn_shapes_preserve_mismatches(self):
        inv = {'schema_version': 1, 'tensors': [matrix('attn_qkv.weight',2560,10240,'Q6_K'),
                                              matrix('attn_gate.weight',2560,6144)]}
        result = map_contracts(inv)
        self.assertEqual(result['counts'], {'gdn': 1})
        row = result['layers'][0]
        self.assertEqual(row['source_weights'][0]['logical_rows_columns'], [10240,2560])
        self.assertTrue(any('input columns 2560, required 5120' in r for r in row['reasons']))
        self.assertEqual(row['decision'], 'incompatible_direct_reuse')

    def test_attention_width_and_interleave_are_explicit(self):
        inv = {'schema_version': 1, 'tensors': [matrix('attn_q.weight',2560,12288,'IQ4_XS'),
                                              matrix('attn_k.weight',2560,512,'Q6_K'),
                                              matrix('attn_v.weight',2560,512,'Q6_K')]}
        row = map_contracts(inv)['layers'][0]
        self.assertTrue(any('output rows 512, required 1024' in r for r in row['reasons']))
        self.assertTrue(any('interleave by head' in r for r in row['reasons']))

    def test_matching_dimensions_and_codec_label_do_not_prove_planes(self):
        inv = {'schema_version': 1, 'tensors': [matrix('attn_qkv.weight',5120,10240,'Q4G64_F16S'),
                                              matrix('attn_gate.weight',5120,6144,'Q5G64_F16S')]}
        row = map_contracts(inv)['layers'][0]
        self.assertEqual(row['decision'], 'incompatible_direct_reuse')
        self.assertTrue(any('not a validated NInfer RowSplit parent' in r for r in row['reasons']))

    def test_missing_duplicate_ambiguous_and_invalid_shapes_fail(self):
        base = {'schema_version': 1, 'tensors': [matrix('attn_qkv.weight',2560,10240),
                                               matrix('attn_gate.weight',2560,6144)]}
        cases = [ {'schema_version':2,'tensors':base['tensors']},
                  {'schema_version':1,'tensors':[]},
                  {'schema_version':1,'tensors':base['tensors'][:1]},
                  {'schema_version':1,'tensors':base['tensors']+[base['tensors'][0]]},
                  {'schema_version':1,'tensors':base['tensors']+[matrix('attn_q.weight',2560,12288)]}]
        for shape in ([0,10240],[True,10240],[2560],[-1,10240]):
            inv=copy.deepcopy(base);inv['tensors'][0]['shape_fastest_dimension_first']=shape;cases.append(inv)
        for inv in cases:
            with self.subTest(inv=inv), self.assertRaises(ValueError): map_contracts(inv)
