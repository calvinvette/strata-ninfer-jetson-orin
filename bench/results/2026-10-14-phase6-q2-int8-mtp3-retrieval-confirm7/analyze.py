#!/usr/bin/env python3
"""Validate the exact-answer Q2_0 MTP-off versus MTP3 paired confirmation."""
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from summarize_controls import interval, measured, metrics

HERE = Path(__file__).resolve().parent
RUN = HERE / 'run-retry1'
EXPECTED = ('EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, '
            'LATE=INDIGO-LANTERN-907, SUM=1768')


def canonical_args(args):
    output = []
    index = 0
    while index < len(args):
        if args[index] in ('--mtp', '--mtp-max-t'):
            index += 2
        elif args[index] == '--spec':
            output.extend(['--spec', '{mtp}'])
            index += 2
        else:
            output.append(args[index])
            index += 1
    return output


def clock_ranges(samples):
    gpu, cpu, emc = [], [], []
    for sample in samples:
        clocks = sample.get('clock_observations') or {}
        gpu_hz = (clocks.get('gpu') or {}).get('hz')
        if isinstance(gpu_hz, int):
            gpu.append(gpu_hz)
        for item in (clocks.get('cpu') or {}).values():
            if isinstance(item.get('hz'), int):
                cpu.append(item['hz'])
        item = clocks.get('emc') or {}
        if isinstance(item.get('hz'), int):
            emc.append(item['hz'])
    def bounds(values):
        return {'samples': len(values), 'minimum_hz': min(values) if values else None,
                'maximum_hz': max(values) if values else None}
    return {'gpu': bounds(gpu), 'cpu_all_cores': bounds(cpu), 'emc': bounds(emc)}


def main():
    plan = json.loads((RUN / 'campaign.json').read_text())
    workload_data = json.loads((HERE / 'workloads.json').read_text())
    workload = workload_data['workloads'][0]
    assert workload['cell'] == 'heldout-retrieval-arithmetic-512'
    assert workload['prompt_tokens'] == 512 and workload['expected_suffix_sum'] == 1768
    assert len(plan['runs']) == 14 and all(row['status'] == 'pass' for row in plan['runs'])
    configs = {}
    for variant in ('baseline', 'candidate'):
        directory = RUN / f'block-0-{variant}'
        configs[variant] = json.loads((directory / 'server-config.json').read_text())
        args = configs[variant]['args']
        assert args[args.index('--kv') + 1] == 'int8'
        assert args[args.index('--expert-cache') + 1] == '3000'
    assert canonical_args(configs['baseline']['args']) == canonical_args(configs['candidate']['args'])
    for key in ('exe', 'cwd', 'tokenizer', 'draft_vocab', 'env', 'cuda', 'lib_dirs'):
        assert configs['baseline'].get(key) == configs['candidate'].get(key), key

    pairs = []
    cgroup_max = {'low': 0, 'high': 0, 'max': 0, 'oom': 0, 'oom_kill': 0}
    supervisor_host_min = float('inf')
    supervisor_admit_min = float('inf')
    request_host_min = float('inf')
    temperatures = []
    for block in range(7):
        variants = {}
        for variant in ('baseline', 'candidate'):
            directory = RUN / f'block-{block}-{variant}'
            rows = measured(directory / 'requests.json')
            assert len(rows) == 1
            row = next(iter(rows.values()))
            assert row['cell'] == workload['cell'] and row['status'] == 'pass'
            content = row['response']['choices'][0]['message'].get('content', '').strip()
            assert content == EXPECTED, (block, variant, content)
            observation = metrics(row)
            assert observation['prompt_tokens'] == 512 and observation['completion_tokens'] == 47
            engine = row['metrics_after']['engine']
            assert engine['kv'] == 'int8' and engine['expert_slots'] == 3000
            expected_mtp = 0 if variant == 'baseline' else 3
            assert engine.get('mtp_max') == expected_mtp, (variant, engine.get('mtp_max'))
            samples = [json.loads(line) for line in (directory / 'memory.jsonl').read_text().splitlines()]
            selected = [sample for sample in samples
                        if row['request_start_monotonic_s'] <= sample['monotonic_s'] <= row['request_end_monotonic_s']]
            request_available = min(sample['available_bytes'] for sample in selected)
            request_host_min = min(request_host_min, request_available / 2**30)
            supervisor = json.loads((directory / 'result.json').read_text())
            assert supervisor['status'] == 'pass'
            supervisor_host_min = min(supervisor_host_min, supervisor['minimum_available_bytes'] / 2**30)
            supervisor_admit_min = min(supervisor_admit_min,
                                       supervisor['minimum_admission_available_bytes'] / 2**30)
            for sample in samples:
                for cg in sample.get('cgroups', []):
                    events = cg.get('memory_events', {})
                    for name in cgroup_max:
                        cgroup_max[name] = max(cgroup_max[name], events.get(name, 0))
            for match in re.finditer(r'\btj@([0-9.]+)C', (directory / 'tegrastats.txt').read_text()):
                temperatures.append(float(match.group(1)))
            observation.update({
                'drafted': observation.get('drafted'), 'accepted': observation.get('accepted'),
                'actual_kv': engine['kv'], 'actual_expert_slots': engine['expert_slots'],
                'actual_mtp_max': engine.get('mtp_max'),
                'request_minimum_host_availability_gib': request_available / 2**30,
                'clocks_during_request': clock_ranges(selected),
                'content': content,
            })
            variants[variant] = observation
        assert variants['baseline']['content'] == variants['candidate']['content'] == EXPECTED
        pair = {'block': block, 'baseline': variants['baseline'], 'candidate': variants['candidate']}
        for metric in ('decode_tps', 'prompt_tps', 'client_ttft_s', 'client_total_s'):
            pair[metric + '_ratio'] = variants['candidate'][metric] / variants['baseline'][metric]
        pairs.append(pair)

    analysis = {
        'schema': 1,
        'scope': 'seven-block held-out Q2_0 int8-KV MTP3 confirmation; request timing plus exact retrieval oracle',
        'date': '2026-10-14', 'seed': plan['seed'], 'blocks': 7,
        'prompt_tokens': 512, 'completion_tokens': 47, 'expected_answer': EXPECTED,
        'prompt_content_sha256': hashlib.sha256(workload['messages'][0]['content'].encode()).hexdigest(),
        'workload_file_sha256': hashlib.sha256((HERE / 'workloads.json').read_bytes()).hexdigest(),
        'binary_sha256': hashlib.sha256(Path(configs['baseline']['exe']).read_bytes()).hexdigest(),
        'model': configs['baseline']['args'][configs['baseline']['args'].index('--native') + 1],
        'ple_shard': configs['baseline']['args'][configs['baseline']['args'].index('--ple-gguf') + 1],
        'mtp_pack': configs['candidate']['args'][configs['candidate']['args'].index('--mtp') + 1],
        'model_and_pack_sha256': (HERE / 'model-checksums.txt').read_text().splitlines(),
        'actual_kv': 'int8', 'actual_expert_slots': 3000,
        'all_cells_passed': True, 'all_14_measured_answers_exact': True,
        'minimum_supervisor_host_availability_gib': supervisor_host_min,
        'minimum_supervisor_admission_availability_gib': supervisor_admit_min,
        'minimum_request_host_availability_gib': request_host_min,
        'maximum_cgroup_events': cgroup_max,
        'tegrastats_tj_c_range': [min(temperatures), max(temperatures)],
        'comparisons': {}, 'paired_blocks': pairs,
        'limitations': [
            'one held-out task and one prompt length; no general profile qualification',
            'no request-attributed energy; clocks were dynamic',
            'MTP acceptance and performance are workload dependent',
        ],
    }
    for metric in ('decode_tps', 'prompt_tps', 'client_ttft_s', 'client_total_s'):
        ratios = [pair[metric + '_ratio'] for pair in pairs]
        analysis['comparisons'][metric] = {
            'baseline_median': statistics.median(pair['baseline'][metric] for pair in pairs),
            'candidate_median': statistics.median(pair['candidate'][metric] for pair in pairs),
            'median_paired_percent_change': (statistics.median(ratios) - 1) * 100,
            'paired_bootstrap_95_interval_percent': [(value - 1) * 100 for value in interval(ratios, 20261015)],
            'block_percent_changes': [(value - 1) * 100 for value in ratios],
        }
    analysis['drafted_per_block'] = [pair['candidate']['drafted'] for pair in pairs]
    analysis['accepted_per_block'] = [pair['candidate']['accepted'] for pair in pairs]
    analysis['clock_scope'] = {
        'gpu_samples_across_requests': sum(pair[v]['clocks_during_request']['gpu']['samples']
                                           for pair in pairs for v in ('baseline', 'candidate')),
        'emc': 'unavailable: debugfs clock read denied; per-sample status retained in memory.jsonl',
        'policy': 'read-only; no clock controls changed',
    }
    (HERE / 'analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
    print(json.dumps({key: analysis[key] for key in ('comparisons', 'minimum_supervisor_host_availability_gib',
          'minimum_supervisor_admission_availability_gib', 'maximum_cgroup_events',
          'drafted_per_block', 'accepted_per_block')}, indent=2))


if __name__ == '__main__':
    main()
