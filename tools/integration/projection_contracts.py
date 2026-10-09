"""Map source GGUF projections to pinned NInfer two-parent contracts; no execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

NINFER_REVISION = 'b07248f2528125aeda7550055580204541f1714c'
PROFILES = {
    'gdn': {
        'operator': 'ninfer::ops::gdn_input_proj(two-parent)',
        'reference': 'reference/ninfer/include/ninfer/ops/gdn_input_proj.h',
        'input_columns': 5120,
        'logical_output_rows': {'attn_qkv.weight': 10240, 'attn_gate.weight': 6144},
        'required_parents': [
            {'rows': 4096, 'columns': 5120, 'format': 'Q4G64_F16S', 'layout': 'RowSplit'},
            {'rows': 12288, 'columns': 5120, 'format': 'Q5G64_F16S', 'layout': 'RowSplit'}],
        'layout_requirement': 'qk parent plus concatenated value/z parent; source QKV and gate parents differ',
    },
    'attention': {
        'operator': 'ninfer::ops::attn_input_proj(two-parent)',
        'reference': 'reference/ninfer/include/ninfer/ops/attn_input_proj.h',
        'input_columns': 5120,
        'logical_output_rows': {'attn_q.weight': 12288, 'attn_k.weight': 1024, 'attn_v.weight': 1024},
        'required_parents': [
            {'rows': 7168, 'columns': 5120, 'format': 'Q4G64_F16S', 'layout': 'RowSplit'},
            {'rows': 7168, 'columns': 5120, 'format': 'Q5G64_F16S', 'layout': 'RowSplit'}],
        'layout_requirement': 'contiguous query/key and gate/value parents; Strata q/gate rows interleave by head',
    },
}


def map_contracts(inventory):
    if inventory.get('schema_version') != 1:
        raise ValueError('unsupported inventory schema')
    tensors = inventory.get('tensors')
    if not isinstance(tensors, list) or not tensors:
        raise ValueError('missing tensor inventory')
    by_layer, seen = {}, set()
    for tensor in tensors:
        symbol = tensor['symbol']
        if symbol in seen:
            raise ValueError(f'duplicate symbol: {symbol}')
        seen.add(symbol)
        match = re.fullmatch(r'blk\.(\d+)\.(.+)', symbol)
        if match:
            by_layer.setdefault(int(match[1]), {})[match[2]] = tensor
    if not by_layer:
        raise ValueError('no layer tensors')
    results = []
    for layer, source in sorted(by_layer.items()):
        gdn, attention = 'attn_qkv.weight' in source, 'attn_q.weight' in source
        if gdn == attention:
            raise ValueError(f'layer {layer}: missing or ambiguous projection family')
        family = 'gdn' if gdn else 'attention'
        profile = PROFILES[family]
        reasons, weights = [], []
        for suffix, expected_rows in profile['logical_output_rows'].items():
            if suffix not in source:
                raise ValueError(f'layer {layer}: missing {suffix}')
            t = source[suffix]
            shape = t.get('shape_fastest_dimension_first')
            if (not isinstance(shape, list) or len(shape) != 2 or
                    any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in shape)):
                raise ValueError(f"invalid matrix shape: {t['symbol']}")
            columns, rows = shape
            if columns != profile['input_columns']:
                reasons.append(f"{suffix}: input columns {columns}, required {profile['input_columns']}")
            if rows != expected_rows:
                reasons.append(f'{suffix}: output rows {rows}, required {expected_rows}')
            codec = t.get('format')
            if not isinstance(codec, str) or not codec:
                raise ValueError(f"missing codec: {t['symbol']}")
            # This descriptor is explicitly GGUF source data. Even a misleading
            # codec name cannot establish RowSplit planes or activation precision.
            reasons.append(f'{suffix}: source GGUF {codec} is not a validated NInfer RowSplit parent')
            weights.append({'symbol': t['symbol'], 'source_format': codec,
                            'source_ggml_type_id': t['ggml_type_id'],
                            'logical_rows_columns': [rows, columns]})
        reasons.append(profile['layout_requirement'])
        results.append({'layer': layer, 'family': family, 'operator': profile['operator'],
                        'decision': 'incompatible_direct_reuse', 'source_weights': weights,
                        'required_parents': profile['required_parents'], 'reasons': reasons,
                        'activation_contract': 'NInfer requires contiguous BF16; source headers do not validate runtime activations'})
    return {'schema_version': 1, 'ninfer_revision': NINFER_REVISION,
            'scope': 'source-header contract map for pinned two-parent projections only; not runtime plane validation or conversion qualification',
            'excluded': 'single-parent NInfer specializations, other operators/codecs, state, numerical accuracy, performance',
            'counts': dict(Counter(r['family'] for r in results)), 'layers': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-direct-profile', action='store_true',
                        help='exit2 after retaining the report if any layer is incompatible')
    args = parser.parse_args()
    result = map_contracts(json.loads(args.inventory.read_text()))
    result['inventory_sha256'] = hashlib.sha256(args.inventory.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'counts': result['counts'], 'decision': 'incompatible_direct_reuse'}))
    return 2 if args.require_direct_profile else 0


if __name__ == '__main__':
    raise SystemExit(main())
