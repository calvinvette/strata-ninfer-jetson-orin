#!/usr/bin/env python3
"""Compare same-seed layer-21 owner captures with and without the layer-31 selector."""
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SELECTOR = ROOT / 'layer21-position515-expert22-chain-128pos'
DEFAULT_DIRECT = ROOT / 'layer21-position515-direct-division-control-128pos'

def read_json(path):
    return json.loads(path.read_text())

def summarize(name, path):
    campaign = read_json(path / 'campaign.json')
    by_name = {r['name']: r for r in campaign['runs']}
    selected = read_json(path / 'selected-position-analysis.json')['arms']
    result = {'binary_sha256': campaign['binary_sha256'], 'seed': campaign['seed'],
              'selector_layer': campaign.get('native_cpu_q8_1_reciprocal_silu_layer'),
              'selector_expert': campaign.get('native_cpu_q8_1_reciprocal_silu_expert'),
              'runs': {k: {'status': v['status'], 'minimum_available_bytes': v['minimum_available_bytes'],
                           'elapsed_s': v['elapsed_s']} for k, v in by_name.items()},
              'arms': {}}
    for arm in ('adaptive-cap8', 'delayed-control'):
        route_rows = [json.loads(line) for line in
                      (path / arm / 'result/all-layer-selected-positions.jsonl').read_text().splitlines()]
        rows = [r for r in route_rows if r.get('layer') == 21 and r.get('position') == 515]
        if len(rows) != 2:
            raise ValueError(f'{name}/{arm}: expected initial and recovery rows, found {len(rows)}')
        expert_rank = rows[0]['ids'].index(132)
        if rows[1]['ids'].index(132) != expert_rank:
            raise ValueError(f'{name}/{arm}: expert 132 changed route rank')
        moe = read_json(path / arm / 'result/layer21-moe-analysis.json')['position_comparisons']['515']
        input_analysis = read_json(path / 'moe-input-analysis.json')['arms'][arm]
        position = selected[arm]['positions']['515']
        result['arms'][arm] = {
            'expert_132_rank': expert_rank,
            'expert_132_owner_initial': rows[0]['route_kind'][expert_rank],
            'expert_132_owner_recovery': rows[1]['route_kind'][expert_rank],
            'owner_changed_layers': position['owner_difference_layers'],
            'routes_and_weights_identical': moe['routes_and_router_weights_identical'],
            'expert_132_output': moe['per_expert_rank'][str(expert_rank)]['output'],
            'shared_expert_output': moe['shared_expert_output'],
            'combined_output': moe['combined_moe_output_before_residual'],
            'first_differing_moe_input_layer': input_analysis['first_differing_layer'],
            'short_recovery_token_mismatches': selected[arm]['short_recovery_token_id_differences'],
            'first_gdn_difference_ordinals': selected[arm]['first_gdn_difference_ordinals'],
        }
    return result

def adaptive_cross_configuration(selector_path, direct_path):
    selector = read_json(selector_path / 'adaptive-cap8/result/requests.json')['requests']
    direct = read_json(direct_path / 'adaptive-cap8/result/requests.json')['requests']
    request_ids_identical = len(selector) == len(direct) and all(
        a['name'] == b['name'] and a['ids'] == b['ids'] for a, b in zip(selector, direct))
    def gdn_hashes(path):
        return [line.split('STATE_HASH_GDN ', 1)[1].strip()
                for line in (path / 'adaptive-cap8/result/service.log').read_text().splitlines()
                if 'STATE_HASH_GDN ' in line]
    selector_gdn = gdn_hashes(selector_path)
    direct_gdn = gdn_hashes(direct_path)
    raw_names = ('verify-moe-routes.jsonl', 'verify-moe-parts.bin', 'verify-moe-output.bin')
    raw_hashes_identical = all(
        (selector_path / 'adaptive-cap8/result' / name).read_bytes() ==
        (direct_path / 'adaptive-cap8/result' / name).read_bytes() for name in raw_names)
    return {
        'request_names_and_token_ids_identical': request_ids_identical,
        'request_count': len(selector),
        'gdn_hash_records_identical': selector_gdn == direct_gdn,
        'gdn_hash_record_count': len(selector_gdn),
        'layer21_capture_bytes_identical': raw_hashes_identical,
        'layer21_capture_files': list(raw_names),
    }

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--selector-run', type=Path, default=DEFAULT_SELECTOR)
parser.add_argument('--direct-division-run', type=Path, default=DEFAULT_DIRECT)
parser.add_argument('--output', type=Path, default=ROOT / 'layer21-selector-vs-direct-division.json')
args = parser.parse_args()
result = {'scope': 'same-seed Orin pair comparison at Coder IQ1_M model layer 21, absolute position 515',
          'selector_arm': summarize('selector', args.selector_run),
          'direct_division_arm': summarize('direct_division', args.direct_division_run),
          'adaptive_cross_configuration': adaptive_cross_configuration(args.selector_run, args.direct_division_run)}
out = args.output
out.write_text(json.dumps(result, indent=2) + '\n')
print(out)
for label in ('selector_arm', 'direct_division_arm'):
    item = result[label]
    print(label, json.dumps({k:item['arms']['adaptive-cap8'][k] for k in ('expert_132_rank','expert_132_owner_initial','expert_132_owner_recovery','routes_and_weights_identical','first_differing_moe_input_layer','short_recovery_token_mismatches','first_gdn_difference_ordinals')}))
