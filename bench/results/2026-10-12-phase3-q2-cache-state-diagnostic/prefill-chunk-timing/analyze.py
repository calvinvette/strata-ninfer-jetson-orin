"""Recompute the paired trace-free prefill-chunk timing summary."""
import hashlib
import json
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
rows = json.loads((HERE / 'runs.json').read_text())
by_name = {row['cell']: row for row in rows}
assert len(rows) == 16

def bootstrap_interval(values, seed):
    rng = random.Random(seed)
    samples = [statistics.median(rng.choices(values, k=len(values))) for _ in range(50000)]
    samples.sort()
    return [samples[int(0.025 * len(samples))], samples[int(0.975 * len(samples))]]

pairs = []
for pair in range(1, 8):
    a = by_name[f'pair{pair:02d}-chunk64']
    b = by_name[f'pair{pair:02d}-chunk512']
    assert a['supervisor_status'] == b['supervisor_status'] == 'pass'
    assert a['prompt_sha256'] == b['prompt_sha256']
    assert a['generated_ids_sha256'] == b['generated_ids_sha256']
    assert a['generated_ids'] == b['generated_ids']
    assert len(a['generated_ids']) == len(b['generated_ids']) == 8
    pairs.append({
        'pair': pair,
        'chunk64_client_elapsed_s': a['client_elapsed_s'],
        'chunk512_client_elapsed_s': b['client_elapsed_s'],
        'client_elapsed_delta_s': b['client_elapsed_s'] - a['client_elapsed_s'],
        'client_elapsed_relative_delta_pct': 100 * (b['client_elapsed_s'] / a['client_elapsed_s'] - 1),
        'chunk64_prompt_ms': a['usage']['prompt_ms'],
        'chunk512_prompt_ms': b['usage']['prompt_ms'],
        'prompt_delta_ms': b['usage']['prompt_ms'] - a['usage']['prompt_ms'],
        'chunk64_decode_ms': a['usage']['decode_ms'],
        'chunk512_decode_ms': b['usage']['decode_ms'],
        'decode_delta_ms': b['usage']['decode_ms'] - a['usage']['decode_ms'],
        'outputs_identical': True,
        'minimum_available_gib': min(a['minimum_available_bytes'], b['minimum_available_bytes']) / 1024**3,
    })

metrics = {}
for name, key, seed in (
    ('client_elapsed_relative_delta_pct', 'client_elapsed_relative_delta_pct', 31),
    ('prompt_delta_ms', 'prompt_delta_ms', 32),
    ('decode_delta_ms', 'decode_delta_ms', 33),
):
    values = [row[key] for row in pairs]
    metrics[name] = {
        'median': statistics.median(values),
        'paired_bootstrap_95_interval': bootstrap_interval(values, seed),
        'samples': values,
    }

clock_values = {'cpu_hz': [], 'gpu_hz': [], 'emc_hz': []}
for row in rows:
    if not row['cell'].startswith('pair'):
        continue
    path = HERE / row['cell'] / 'memory.jsonl'
    for line in path.read_text().splitlines():
        sample = json.loads(line).get('clock_observations') or {}
        clock_values['cpu_hz'].extend(v['hz'] for v in sample.get('cpu', {}).values())
        if sample.get('gpu', {}).get('hz'):
            clock_values['gpu_hz'].append(sample['gpu']['hz'])
        if sample.get('emc', {}).get('hz'):
            clock_values['emc_hz'].append(sample['emc']['hz'])
clock_ranges = {key: ([min(values), max(values)] if values else None)
                for key, values in clock_values.items()}

engine = ROOT / 'build/integration/candidate/strata'
summary = {
    'design': 'Seven randomized paired trace-free process blocks; exact 511-token prefix, 8 greedy output tokens, 3,000 requested expert-cache slots and context 640; one warmup per chunk arm.',
    'artifacts': {
        'engine_sha256': hashlib.sha256(engine.read_bytes()).hexdigest(),
        'model_repository_revision': '5348543e0147355ac9cbcb031184a3546350988e',
        'model_shards': [
            {'name': 'Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf', 'sha256': '69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720'},
            {'name': 'Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf', 'sha256': '316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113'},
        ],
        'prompt_tokens': 511,
        'prompt_sha256': by_name['pair01-chunk64']['prompt_sha256'],
        'output_tokens': 8,
        'temperature': 0,
    },
    'randomization': json.loads((HERE / 'order.json').read_text()),
    'paired_metrics': metrics,
    'minimum_available_gib': min(row['minimum_available_gib'] for row in pairs),
    'clock_ranges_hz': clock_ranges,
    'same_output_hash': by_name['pair01-chunk64']['generated_ids_sha256'],
    'pairs': pairs,
    'limits': [
        'One synthetic exact-length prompt and one model/capacity/context cell.',
        'Clocks were observed dynamically; no clocks were controlled.',
        'No energy measurement; timing runner had no engine owner/state tracing.',
        'Separate state diagnostics on this same prompt found repeatable persistent-state differences across prefill chunks; matching these eight tokens is not a quality or state-parity qualification.',
    ],
}
(HERE / 'analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'client_elapsed_relative_delta_pct': metrics['client_elapsed_relative_delta_pct'],
                  'prompt_delta_ms': metrics['prompt_delta_ms'],
                  'decode_delta_ms': metrics['decode_delta_ms'],
                  'minimum_available_gib': summary['minimum_available_gib'],
                  'clock_ranges_hz': clock_ranges}, indent=2))
