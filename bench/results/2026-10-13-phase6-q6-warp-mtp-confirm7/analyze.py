#!/usr/bin/env python3
"""Validate and summarize the seven-block 2x2 held-out confirmation."""
import hashlib
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'
CONDITIONS = ('baseline-mtp0', 'warp-mtp0', 'baseline-mtp4', 'warp-mtp4')
BOOTSTRAPS = 200_000


def median(values):
    return statistics.median(values)


def interval(values, seed):
    rng = random.Random(seed)
    samples = [median([rng.choice(values) for _ in values]) for _ in range(BOOTSTRAPS)]
    samples.sort()
    return [samples[int((BOOTSTRAPS - 1) * .025)],
            samples[int((BOOTSTRAPS - 1) * .975)]]


def delta(candidate, baseline):
    return 100 * (candidate / baseline - 1)


def output(row):
    return row['response']['choices'][0]['message']['content']


campaign = json.loads((RUN / 'experiment.json').read_text())
assert campaign['planned_blocks'] == 7 and len(campaign['runs']) == 28
assert all(row['status'] == 'pass' and row['supervisor_returncode'] == 0
           for row in campaign['runs']), 'campaign contains failed or incomplete cells'
assert campaign['seed'] == 202610131

configs = {name: json.loads((ROOT / f'{name}-config.json').read_text())
           for name in CONDITIONS}
for field in ('exe', 'tokenizer', 'model_name', 'cuda'):
    assert len({cfg[field] for cfg in configs.values()}) == 1, field
for cfg in configs.values():
    assert cfg['args'][cfg['args'].index('--max-context') + 1] == '8192'
    assert cfg['args'][cfg['args'].index('--expert-cache') + 1] == '3000'

workload = json.loads((ROOT / 'workloads.json').read_text())['workloads']
warmup = json.loads((ROOT / 'warmup-workloads.json').read_text())['workloads']
assert len(workload) == len(warmup) == 1
assert (workload[0]['prompt_tokens'], workload[0]['generate_tokens']) == (2048, 128)
assert (warmup[0]['prompt_tokens'], warmup[0]['generate_tokens']) == (512, 1)

requests, supervisors, hashes, slots = {}, {}, {}, []
minimum_host = minimum_effective = 2**63
for block in range(7):
    requests[block] = {}
    for condition in CONDITIONS:
        base = RUN / f'block-{block}-{condition}'
        request = json.loads((base / 'requests.json').read_text())
        measured = [row for row in request['checks'] if not row['warmup']]
        warm_rows = [row for row in request['checks'] if row['warmup']]
        assert len(measured) == len(warm_rows) == 1
        row, warm_row = measured[0], warm_rows[0]
        assert row['status'] == warm_row['status'] == 'pass'
        assert row['response']['usage']['prompt_tokens'] == 2048
        assert row['response']['usage']['completion_tokens'] == 128
        assert warm_row['response']['usage']['prompt_tokens'] == 512
        assert warm_row['response']['usage']['completion_tokens'] == 1
        assert row['response']['timings']['cache_n'] == 0
        requests[block][condition] = row
        hashes[(block, condition)] = hashlib.sha256(output(row).encode()).hexdigest()
        metrics = row['response']['timings']
        mtp_on = condition.endswith('mtp4')
        assert bool(metrics.get('draft_n', 0)) == mtp_on
        if mtp_on:
            assert metrics.get('draft_n_accepted', 0) > 0

        supervisor = json.loads((base / 'supervisor/result.json').read_text())
        assert supervisor['status'] == 'pass' and supervisor['returncode'] == 0
        assert supervisor['minimum_available_bytes'] >= 6 * 1024**3
        assert supervisor['minimum_admission_available_bytes'] >= 6 * 1024**3
        minimum_host = min(minimum_host, supervisor['minimum_available_bytes'])
        minimum_effective = min(minimum_effective,
                                supervisor['minimum_admission_available_bytes'])
        supervisors[(block, condition)] = supervisor
        import re
        engine = (base / 'engine.log').read_text(errors='replace')
        found = re.search(r'expert cache (\d+) slots', engine)
        assert found, f'missing cache admission record {block}/{condition}'
        slots.append(int(found.group(1)))

    for mtp in (0, 4):
        assert hashes[(block, f'baseline-mtp{mtp}')] == hashes[(block, f'warp-mtp{mtp}')], (
            f'Q6 warp output differs at fixed MTP level in block {block}, window {mtp}')

assert len(set(slots)) == 1 and slots[0] == 3903, slots

metrics = ('request_ms', 'prompt_ms', 'decode_ms', 'client_elapsed_ms')
def value(row, name):
    if name == 'request_ms':
        timing = row['response']['timings']
        return timing['prompt_ms'] + timing['predicted_ms']
    if name in ('prompt_ms', 'decode_ms'):
        key = 'predicted_ms' if name == 'decode_ms' else name
        return row['response']['timings'][key]
    return row['client_elapsed_s'] * 1000

effects = {}
for mtp in (0, 4):
    label = f'mtp{mtp}'
    effects[label] = {}
    for metric in metrics:
        paired = [delta(value(requests[b][f'warp-mtp{mtp}'], metric),
                        value(requests[b][f'baseline-mtp{mtp}'], metric))
                  for b in range(7)]
        effects[label][metric] = {
            'paired_candidate_delta_pct': paired,
            'median_paired_delta_pct': median(paired),
            'paired_bootstrap_95_pct': interval(paired, 202610131 + mtp * 10 + metrics.index(metric)),
        }

interaction = {}
for metric in metrics:
    per_block = []
    for b in range(7):
        warp0 = value(requests[b]['warp-mtp0'], metric)
        base0 = value(requests[b]['baseline-mtp0'], metric)
        warp4 = value(requests[b]['warp-mtp4'], metric)
        base4 = value(requests[b]['baseline-mtp4'], metric)
        per_block.append(100 * ((warp4 / base4) / (warp0 / base0) - 1))
    interaction[metric] = {
        'per_block_pct': per_block,
        'median_pct': median(per_block),
        'paired_bootstrap_95_pct': interval(per_block, 202610191 + metrics.index(metric)),
    }

report = {
    'scope': 'seven-block randomized confirmation; held-out 2048/128 incident workload; Q6_K warp-dequant × MTP off/window4',
    'seed': campaign['seed'], 'blocks': 7, 'conditions': list(CONDITIONS),
    'binary_sha256': hashlib.sha256(Path(configs[CONDITIONS[0]]['exe']).read_bytes()).hexdigest(),
    'all_28_runs_passed': True,
    'q6_warp_output_parity_at_each_fixed_mtp_level': True,
    'mtp_off_vs_window4_output_parity': all(
        hashes[(b, 'baseline-mtp0')] == hashes[(b, 'baseline-mtp4')] for b in range(7)),
    'output_sha256_by_block_and_mtp': {
        str(b): {f'mtp{mtp}': hashes[(b, f'baseline-mtp{mtp}')] for mtp in (0, 4)}
        for b in range(7)},
    'cache_slots': slots, 'minimum_host_available_bytes': minimum_host,
    'minimum_effective_available_bytes': minimum_effective,
    'per_condition_medians': {
        condition: {metric: median([value(requests[b][condition], metric) for b in range(7)])
                    for metric in metrics}
        for condition in CONDITIONS
    },
    'warp_effects': effects, 'warp_by_mtp_interaction': interaction,
    'bootstrap_replicates': BOOTSTRAPS,
    'qualification': ('Seven-pair Q6 warp timing confirmation at each fixed MTP level for this one held-out prompt and model/context/cache configuration. '
                      'MTP-off and MTP-window4 text differ deterministically; this is a Phase 5 output-equivalence failure requiring state-level follow-up. '
                      'Do not combine MTP-level timing as a quality-qualified optimization or promote a default.'),
}
(RUN / 'confirmation-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
for mtp in ('mtp0', 'mtp4'):
    effect = effects[mtp]['request_ms']
    print(mtp, 'request delta', f"{effect['median_paired_delta_pct']:.3f}%",
          'bootstrap', [round(x, 3) for x in effect['paired_bootstrap_95_pct']])
print('interaction request', f"{interaction['request_ms']['median_pct']:.3f}%",
      'bootstrap', [round(x, 3) for x in interaction['request_ms']['paired_bootstrap_95_pct']])
print('minimum host/effective GiB', round(minimum_host / 2**30, 3),
      round(minimum_effective / 2**30, 3))
