#!/usr/bin/env python3
"""Compare adaptive and delayed Coder runs at every shared accepted prefix."""
import argparse
import json
import re
from pathlib import Path

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
ARMS = ('adaptive-cap8', 'delayed-control')


def load_arm(root: Path, arm: str):
    run = root / arm
    result = run / 'result'
    requests = json.loads((result / 'requests.json').read_text())['requests']
    prefixes = []
    for line in (result / 'service.log').read_text().splitlines():
        if 'ACCEPTED_PREFIX position=' not in line:
            continue
        match = re.search(r'ACCEPTED_PREFIX position=(\d+).*?tokens=(\d+) state=\{STATE_HASH ([^}]+)\}', line)
        if match is None:
            raise ValueError(f'{arm}: malformed accepted-prefix record')
        fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', match.group(3)))
        if not set(STATE_KEYS) <= fields.keys():
            raise ValueError(f'{arm}: incomplete accepted-prefix state')
        prefixes.append({'position': int(match.group(1)), 'token_id': int(match.group(2)),
                         'state': {key: fields[key] for key in STATE_KEYS}})

    if len(prefixes) != sum(len(row['ids']) for row in requests):
        raise ValueError(f'{arm}: accepted-prefix count does not match generated token count')
    offset, per_request = 0, []
    for row in requests:
        count = len(row['ids'])
        commits = prefixes[offset:offset + count]
        offset += count
        if [x['token_id'] for x in commits] != row['ids']:
            raise ValueError(f'{arm}/{row["name"]}: logged token IDs differ from API tokens')
        per_request.append({'name': row['name'], 'prompt_tokens': row['prompt_tokens'],
                            'token_ids': row['ids'], 'final_state': row['state'],
                            'accepted_prefixes': commits})

    capture = [json.loads(line) for line in (result / 'layer0.jsonl').read_text().splitlines()]
    if not capture or capture[0].get('format') != 'strata-moe-dispatch-v3':
        raise ValueError(f'{arm}: expected current v3 route capture')
    rows = capture[1:]
    if any(row.get('layer') != 1 for row in rows):
        raise ValueError(f'{arm}: route capture includes a layer other than layer 1')
    analysis = json.loads((result / 'analysis.json').read_text())
    supervisor = json.loads((run / 'supervisor' / 'result.json').read_text())
    if supervisor.get('status') != 'pass':
        raise ValueError(f'{arm}: supervisor did not pass')
    if supervisor['minimum_available_bytes'] < 6 * 1024**3 or supervisor['minimum_admission_available_bytes'] < 3 * 1024**3:
        raise ValueError(f'{arm}: memory floor/reserve failed')
    event_maxima = {}
    for line in (run / 'supervisor' / 'memory.jsonl').read_text().splitlines():
        sample = json.loads(line)
        for cgroup in sample.get('cgroups', []):
            if cgroup.get('max_bytes') == 28 * 1024**3:
                for key, value in cgroup.get('memory_events', {}).items():
                    event_maxima[key] = max(event_maxima.get(key, 0), value)
    return {'requests': per_request,
            'adaptive_checks': {'byte_verification_passes': analysis['adaptive_byte_verification_passes'],
                                'residency_verification_passes': analysis['adaptive_residency_verification_passes']},
            'layer1_route_comparison': analysis['route'],
            'within_service_short_recovery': {
                'token_id_differences': sum(a != b for a, b in zip(per_request[0]['token_ids'], per_request[2]['token_ids'])),
                'different_accepted_prefix_states': sum(a['state'] != b['state'] for a, b in zip(per_request[0]['accepted_prefixes'], per_request[2]['accepted_prefixes'])),
                'different_final_state_fields': [key for key in STATE_KEYS if per_request[0]['final_state'].get(key) != per_request[2]['final_state'].get(key)]},
            'layer1_capture': {'format': capture[0]['format'], 'rows': len(rows),
                               'route_kind_counts': {str(kind): sum(1 for row in rows for item in row.get('route_kind', []) if item == kind)
                                                     for kind in sorted({item for row in rows for item in row.get('route_kind', [])})}},
            'supervisor': {'minimum_available_bytes': supervisor['minimum_available_bytes'],
                           'minimum_admission_available_bytes': supervisor['minimum_admission_available_bytes'],
                           'cgroup_event_maxima': event_maxima,
                           'status': supervisor['status']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    campaign = json.loads((args.pair_dir / 'campaign.json').read_text())
    if campaign.get('status') != 'pass' or len(campaign.get('runs', [])) != 2:
        raise ValueError('expected two passing campaign arms')
    arms = {name: load_arm(args.pair_dir, name) for name in ARMS}
    left, right = arms[ARMS[0]]['requests'], arms[ARMS[1]]['requests']
    if len(left) != len(right) or any(a['name'] != b['name'] for a, b in zip(left, right)):
        raise ValueError('request sequence mismatch')
    between = {}
    for a, b in zip(left, right):
        ap, bp = a['accepted_prefixes'], b['accepted_prefixes']
        if len(ap) != len(bp):
            raise ValueError(f'{a["name"]}: accepted-prefix length mismatch')
        first_diff = next((i for i, (x, y) in enumerate(zip(ap, bp)) if x['state'] != y['state']), None)
        between[a['name']] = {
            'token_id_differences': sum(x != y for x, y in zip(a['token_ids'], b['token_ids'])),
            'shared_prefixes_compared': len(ap),
            'state_different_shared_prefixes': sum(x['state'] != y['state'] for x, y in zip(ap, bp)),
            'first_state_difference_index': first_diff,
            'first_state_difference_fields': [] if first_diff is None else [key for key in STATE_KEYS if ap[first_diff]['state'][key] != bp[first_diff]['state'][key]],
        }
    report = {'campaign_status': campaign['status'], 'repository_head': campaign['repository_head'],
              'binary_sha256': campaign['binary_sha256'], 'model_repository': campaign['model_repository'],
              'model_revision': campaign['model_revision'], 'quantization': campaign['quantization'],
              'cpu_expert_selector': 'STRATA_NATIVE_CPU_Q8_1_DOT=all',
              'state_fields_compared': list(STATE_KEYS), 'arms': arms, 'between_arms': between,
              'limits': ['one Coder IQ1_M artifact and one short/long/short/continuation sequence',
                         'Q8_1 mirrors only the three explicitly supported expert format pairs',
                         'no task-quality, timing, energy, or default-policy qualification']}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'between_arms': between,
                      'within_service_short_recovery': {k: v['within_service_short_recovery'] for k, v in arms.items()},
                      'minimum_host_gib': min(v['supervisor']['minimum_available_bytes'] for v in arms.values()) / 1024**3,
                      'minimum_admission_gib': min(v['supervisor']['minimum_admission_available_bytes'] for v in arms.values()) / 1024**3}, indent=2))


if __name__ == '__main__':
    main()
