#!/usr/bin/env python3
"""Compare layer-21 position 515 on one held-out workload with/without selector."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAIRS = {
    'reciprocal_silu_layer31_expert22': ROOT / 'layer21-position515-expert22-heldout-prompt-128pos',
    'direct_division': ROOT / 'layer21-position515-heldout-direct-division-128pos',
}

def read(path): return json.loads(path.read_text())

def arm(path, name):
    campaign = read(path / 'campaign.json')
    selected = read(path / 'selected-position-analysis.json')['arms'][name]
    moe = read(path / name / 'result/layer21-moe-analysis.json')['position_comparisons']['515']
    rows = [json.loads(line) for line in (path / name / 'result/all-layer-selected-positions.jsonl').read_text().splitlines()]
    rows = [r for r in rows if r.get('position') == 515 and r.get('layer') == 21]
    return {
        'campaign_status': campaign['status'],
        'workload_cell': campaign['prompt_workload_cell'],
        'workload_file_sha256': campaign['prompt_workload_file_sha256'],
        'long_token_limit': campaign['long_token_limit'],
        'binary_sha256': campaign['binary_sha256'],
        'recovery_token_mismatches': selected['short_recovery_token_id_differences'],
        'first_gdn_difference_ordinals': selected['first_gdn_difference_ordinals'],
        'layer21_expert132_owner_initial': rows[0]['route_kind'][7],
        'layer21_expert132_owner_recovery': rows[-1]['route_kind'][7],
        'layer21_routes_and_weights_identical': moe['routes_and_router_weights_identical'],
        'layer21_rank_outputs': {rank: {'expert_id': value['initial_expert'],
                                        'initial_sha256': value['output']['initial_f32_sha256'],
                                        'recovery_sha256': value['output']['recovery_f32_sha256'],
                                        'different_values': value['output']['different_values'],
                                        'relative_l2': value['output']['relative_l2']}
                                 for rank, value in moe['per_expert_rank'].items()},
        'layer21_combined_output': moe['combined_moe_output_before_residual'],
        'first_differing_moe_input_layer': read(path / 'moe-input-analysis.json')['arms'][name]['first_differing_layer'],
    }

result = {'scope': 'same-seed paired Orin runs on the same held-out prompt, Coder IQ1_M, layer 21 position 515',
          'selector_adaptive': arm(PAIRS['reciprocal_silu_layer31_expert22'], 'adaptive-cap8'),
          'direct_division_adaptive': arm(PAIRS['direct_division'], 'adaptive-cap8'),
          'selector_delayed_control': arm(PAIRS['reciprocal_silu_layer31_expert22'], 'delayed-control'),
          'direct_division_delayed_control': arm(PAIRS['direct_division'], 'delayed-control')}
for key in ('workload_cell','workload_file_sha256','long_token_limit','binary_sha256'):
    if result['selector_adaptive'][key] != result['direct_division_adaptive'][key]:
        raise ValueError(f'comparison identity mismatch in {key}')
result['adaptive_layer21_combined_outputs_identical_across_selector'] = (
    result['selector_adaptive']['layer21_combined_output']['recovery_f32_sha256'] ==
    result['direct_division_adaptive']['layer21_combined_output']['recovery_f32_sha256'])
out = ROOT / 'heldout-layer21-selector-vs-direct-division.json'
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: {'token_mismatches': v['recovery_token_mismatches'],
                      'first_gdn': v['first_gdn_difference_ordinals'][:1],
                      'owner132': [v['layer21_expert132_owner_initial'],v['layer21_expert132_owner_recovery']],
                      'first_moe_input': v['first_differing_moe_input_layer'],
                      'combined_hash': v['layer21_combined_output']['recovery_f32_sha256']}
                  for k,v in result.items() if isinstance(v,dict) and 'recovery_token_mismatches' in v},indent=2))
print('adaptive layer21 outputs identical across selector:',result['adaptive_layer21_combined_outputs_identical_across_selector'])
