#!/usr/bin/env python3
"""Compare per-layer activations, expert IDs and owners in paired captures."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / 'all-layer-campaign'


def read_rows(path):
    by_layer = {}
    with gzip.open(path, 'rt') as stream:
        header = json.loads(next(stream))
        if header.get('format') != 'strata-moe-dispatch-v2':
            raise RuntimeError(f'{path}: unexpected header {header}')
        for line in stream:
            row = json.loads(line)
            by_layer.setdefault(row['layer'], []).append(row)
    return by_layer


def compare_row(a, b):
    av, bv = a['activation'], b['activation']
    if len(av) != len(bv):
        raise RuntimeError('activation width differs')
    delta = [abs(x - y) for x, y in zip(av, bv)]
    base = sum(abs(x) for x in av)
    common = set(a['ids']) & set(b['ids'])
    ak, bk = dict(zip(a['ids'], a['route_kind'])), dict(zip(b['ids'], b['route_kind']))
    owner_changes = [{'expert': e, 'control': ak[e], 'candidate': bk[e]}
                     for e in sorted(common) if ak[e] != bk[e]]
    return {
        'activation_different_values': sum(x != y for x, y in zip(av, bv)),
        'activation_max_abs': max(delta, default=0.0),
        'activation_rel_l1': sum(delta) / (base + 1e-30),
        'expert_ids_equal': a['ids'] == b['ids'],
        'expert_id_overlap': len(common),
        'route_kind_equal_at_same_position': a['route_kind'] == b['route_kind'],
        'same_expert_owner_changes': owner_changes,
    }


def main():
    campaign = json.loads((CAMPAIGN / 'campaign.json').read_text())
    blocks = []
    for block in range(3):
        control = read_rows(CAMPAIGN / f'block-{block}-delayed-control/all-layers.jsonl.gz')
        candidate = read_rows(CAMPAIGN / f'block-{block}-swap-8/all-layers.jsonl.gz')
        common_layers = sorted(set(control) & set(candidate))
        layers = []
        for layer in common_layers:
            a, b = control[layer], candidate[layer]
            paired = min(len(a), len(b))
            # Each request contributes the first 22 captured rows per layer.
            short_end = min(22, paired)
            row_groups = [('short-512', 0, short_end), ('long-2048', short_end, paired)]
            for request, lo, hi in row_groups:
                if lo >= hi:
                    continue
                rows = [{'row_index': i, **compare_row(a[i], b[i])} for i in range(lo, hi)]
                changed_activations = [i + lo for i, row in enumerate(rows)
                                       if row['activation_different_values']]
                layers.append({
                    'layer': layer, 'request': request, 'paired_rows': len(rows),
                    'activation_rows_different': len(changed_activations),
                    'first_activation_difference_row': changed_activations[0] if changed_activations else None,
                    'expert_id_rows_different': sum(not row['expert_ids_equal'] for row in rows),
                    'same_expert_owner_change_count': sum(len(row['same_expert_owner_changes']) for row in rows),
                    'activation_rel_l1_max': max((row['activation_rel_l1'] for row in rows), default=0.0),
                    'activation_max_abs_max': max((row['activation_max_abs'] for row in rows), default=0.0),
                    'row_details': rows,
                })
        first = {}
        first_owner = {}
        for request in ('short-512', 'long-2048'):
            hit = next((x for x in layers if x['request'] == request and x['activation_rows_different']), None)
            first[request] = None if hit is None else {
                'layer': hit['layer'], 'different_rows': hit['activation_rows_different'],
                'first_row': hit['first_activation_difference_row'],
                'expert_id_rows_different': hit['expert_id_rows_different'],
                'same_expert_owner_change_count': hit['same_expert_owner_change_count'],
            }
            owner_hit = next((x for x in layers if x['request'] == request and
                              x['same_expert_owner_change_count']), None)
            if owner_hit is None:
                first_owner[request] = None
            else:
                row_hit = next(row for row in owner_hit['row_details']
                               if row['same_expert_owner_changes'])
                first_owner[request] = {
                    'layer': owner_hit['layer'], 'row': row_hit['row_index'],
                    'changes': row_hit['same_expert_owner_changes'],
                }
        blocks.append({'block': block, 'captured_layers': common_layers,
                       'control_layer_rows': {str(k): len(control[k]) for k in common_layers},
                       'candidate_layer_rows': {str(k): len(candidate[k]) for k in common_layers},
                       'first_activation_divergence': first,
                       'first_same_expert_owner_change': first_owner, 'layers': layers})
    result = {'campaign_status': campaign['status'], 'binary_sha256': campaign['binary_sha256'],
              'model_repository': campaign['model_repository'], 'model_revision': campaign['model_revision'],
              'model_quantization': campaign['model_quantization'], 'blocks': blocks,
              'limits': ['captured activation values are formatted with %.9g in the service diagnostic',
                         'capture is capped at 4096 rows; omitted layers/rows are not inferred',
                         'route kinds are compared only when the same expert ID is selected']}
    output = CAMPAIGN / 'comparison.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    for block in blocks:
        print('block', block['block'], 'first activation divergence', block['first_activation_divergence'])
    print('wrote', output)


if __name__ == '__main__':
    main()
