#!/usr/bin/env python3
"""Validate exact image-grounding responses and their supervised resources."""
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
oracle = json.loads((HERE / 'oracle.json').read_text())
expected = oracle['expected_exact_response']
fixture_hash = hashlib.sha256((HERE / 'fixture.png').read_bytes()).hexdigest()
rows = []
for name in ('run', 'run-02', 'run-03'):
    result = json.loads((HERE / name / 'result.json').read_text())
    supervisor_name = 'supervisor' if name == 'run' else f'supervisor-{name[-2:]}'
    supervisor = json.loads((HERE / supervisor_name / 'result.json').read_text())
    assert result['response_status'] == 200
    assert result['health']['images'] is True and result['health']['loaded'] is True
    assert result['fixture_sha256'] == fixture_hash
    choice = result['response']['choices'][0]
    usage = result['response']['usage']
    assert choice['message']['content'].strip() == expected
    assert choice['finish_reason'] == 'stop'
    assert usage['prompt_tokens'] == 80 and usage['completion_tokens'] == 17
    assert result['server_returncode_after_stop'] == 0
    assert supervisor['status'] == 'pass' and supervisor['floor_bytes'] == 6 * 1024**3
    assert supervisor['minimum_admission_available_bytes'] >= 6 * 1024**3
    events = {'high': 0, 'max': 0, 'oom': 0, 'oom_kill': 0}
    samples = [json.loads(line) for line in (HERE / supervisor_name / 'memory.jsonl').read_text().splitlines()]
    assert samples
    for sample in samples:
        for cgroup in sample.get('cgroups', []):
            for key in events:
                events[key] = max(events[key], cgroup.get('memory_events', {}).get(key, 0))
    assert not any(events.values())
    rows.append({'run': name, 'status': 'pass', 'response': choice['message']['content'],
        'prompt_tokens': usage['prompt_tokens'], 'completion_tokens': usage['completion_tokens'],
        'request_elapsed_s': result['request_elapsed_s'],
        'minimum_host_available_gib': supervisor['minimum_available_bytes'] / 1024**3,
        'minimum_admission_available_gib': supervisor['minimum_admission_available_bytes'] / 1024**3,
        'memory_samples': len(samples), 'cgroup_event_maxima': events,
        'server_exit_code': result['server_returncode_after_stop']})
analysis = {'scope': 'Three fresh-service exact image-grounding repetitions on the current Coder IQ1_M profile; one 224x224 synthetic image; one request per service.',
    'fixture_sha256': fixture_hash, 'expected_exact_response': expected,
    'independent_oracle': oracle['oracle_basis'], 'all_three_exact': True,
    'all_three_http_200_and_image_enabled': True, 'all_three_clean_teardown': True,
    'median_request_elapsed_s': statistics.median(x['request_elapsed_s'] for x in rows),
    'minimum_host_available_gib': min(x['minimum_host_available_gib'] for x in rows),
    'minimum_admission_available_gib': min(x['minimum_admission_available_gib'] for x in rows),
    'max_cgroup_events': {key: max(x['cgroup_event_maxima'][key] for x in rows) for key in ('high','max','oom','oom_kill')},
    'runs': rows, 'limits': ['One synthetic visual counting task only; this is not broad vision quality or high-resolution support.',
        'The 16-token image-encoder setting was held fixed; no resolution/token sweep was run.',
        'Energy is not process-attributed; no energy claim is made.']}
(HERE / 'analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
print(json.dumps(analysis, indent=2))
