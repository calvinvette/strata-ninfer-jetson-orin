"""Summarize paired request controls, retaining feasibility and metric scopes."""
from collections import defaultdict
import argparse
import csv
import json
import math
from pathlib import Path
import random
import statistics

from request_telemetry import rails_from_lines, window_energy


def interval(values, seed=870126):
    rng = random.Random(seed)
    samples = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(5000))
    return [samples[int(0.025 * len(samples))], samples[int(0.975 * len(samples))]]


def measured(path):
    data = json.loads(path.read_text())
    cells = {}
    for row in data['checks']:
        if row['warmup']:
            continue
        if row['cell'] in cells:
            raise ValueError('expected one measured request per cell/process')
        cells[row['cell']] = row
    return cells


def metrics(row):
    counters = row.get('metrics_after', {}).get('requests', [])
    if not counters:
        raise ValueError('missing per-request engine counters')
    raw = counters[0]
    usage = row['response']['usage']
    if raw['prompt_tokens'] != usage['prompt_tokens'] or raw['output_tokens'] != usage['completion_tokens']:
        raise ValueError('per-request metrics do not match API response')
    if raw.get('reused', 0) or raw.get('prompt_read') != raw['prompt_tokens']:
        raise ValueError('fresh-prefill engine counters do not match workload')
    prompt_ms, decode_ms = raw.get('prompt_ms'), raw.get('decode_ms')
    if not prompt_ms or not decode_ms:
        raise ValueError('missing stage times')
    return {'prompt_tps': raw['prompt_tokens'] * 1000 / prompt_ms,
            'decode_tps': raw['engine_generated'] * 1000 / decode_ms,
            'client_total_s': row['client_elapsed_s'],
            'client_ttft_s': row['stream_observation']['first_visible_delta_s'],
            'drafted': raw.get('drafts_offered'), 'accepted': raw.get('drafts_accepted'),
            'cache_hit_rate': raw.get('hit_rate'), 'logical_file_mb': raw.get('file_mb'),
            'prompt_tokens': raw['prompt_tokens'], 'completion_tokens': usage['completion_tokens']}


def summarize(campaign, clock_path=None):
    plan = json.loads((campaign / 'campaign.json').read_text())
    clocks = [json.loads(line) for line in clock_path.read_text().splitlines()] if clock_path else []
    records, rejected = defaultdict(list), []
    pairs = defaultdict(dict)
    for run in plan['runs']:
        pairs[run['block']][run['variant']] = run
    for block, variants in sorted(pairs.items()):
        if set(variants) != {'baseline', 'candidate'}:
            raise ValueError('unpaired block')
        loaded = {}
        configurations = {}
        for variant, run in variants.items():
            directory = campaign / f'block-{block}-{variant}'
            if run['status'] != 'pass':
                rejected.append({'block': block, 'variant': variant, 'status': run['status'], 'reason': run.get('reason')})
                continue
            loaded[variant] = measured(directory / 'requests.json')
            configurations[variant] = json.loads((directory / 'server-config.json').read_text())
        if len(loaded) != 2:
            continue
        a, b = configurations['baseline'], configurations['candidate']
        for key in ('args', 'tokenizer', 'model_name', 'draft_vocab', 'env'):
            if a.get(key) != b.get(key):
                raise ValueError(f'paired configuration mismatch: {key}')
        if loaded['baseline'].keys() != loaded['candidate'].keys():
            raise ValueError('paired workload mismatch')
        for cell in loaded['baseline']:
            rows = {variant: loaded[variant][cell] for variant in loaded}
            if any(row['status'] != 'pass' for row in rows.values()):
                rejected.append({'block': block, 'cell': cell, 'status': 'fail', 'reason': 'workload qualification failed'})
                continue
            observations = {}
            for variant, row in rows.items():
                observation = metrics(row)
                engine = row['metrics_after']['engine']
                observation.update(expert_slots=engine.get('expert_slots'), expert_cache_mib=engine.get('expert_cache_mib'),
                                   mtp_max=engine.get('mtp_max'), native_spec_capacity=engine.get('spec'),
                                   lookup=engine.get('lookup'), kv=engine.get('kv'))
                for key in ('gpu', 'emc'):
                    selected = [c[key]['hz'] for c in clocks if 'hz' in c.get(key, {}) and
                                row['request_start_monotonic_s'] <= c['monotonic_s'] <= row['request_end_monotonic_s']]
                    observation[key + '_observed_hz'] = {'samples': len(selected),
                        'minimum': min(selected) if selected else None, 'maximum': max(selected) if selected else None}
                memory = [json.loads(line) for line in (campaign / f'block-{block}-{variant}/memory.jsonl').read_text().splitlines()]
                selected = [m for m in memory if row['request_start_monotonic_s'] <= m['monotonic_s'] <= row['request_end_monotonic_s']]
                observation['minimum_available_bytes'] = min(m['available_bytes'] for m in selected) if selected else None
                observation['maximum_swap_used_bytes'] = max(m['swap_used_bytes'] for m in selected) if selected else None
                rail_path = campaign / f'block-{block}-{variant}/tegrastats.txt'
                if rail_path.exists() and memory:
                    epoch_offset = memory[0]['wall_time_s'] - memory[0]['monotonic_s']
                    rails = rails_from_lines(rail_path.read_text().splitlines())
                    observation['rail_energy'] = window_energy(rails,
                        row['request_start_monotonic_s'] + epoch_offset,
                        row['request_end_monotonic_s'] + epoch_offset)
                observations[variant] = observation
            for key in ('expert_slots', 'expert_cache_mib', 'mtp_max', 'native_spec_capacity', 'lookup', 'kv', 'prompt_tokens', 'completion_tokens'):
                if observations['baseline'][key] != observations['candidate'][key]:
                    raise ValueError(f'actual resource/workload mismatch: block {block} {cell} {key}')
            content = {variant: row['response']['choices'][0]['message'] for variant, row in rows.items()}
            records[cell].append({'block': block, **observations,
                                  'api_content_matches': content['baseline'] == content['candidate']})
    summaries = []
    for cell, blocks in records.items():
        result = {'cell': cell, 'paired_blocks': len(blocks),
                  'api_content_matching_blocks': sum(row['api_content_matches'] for row in blocks)}
        for key in ('prompt_tps', 'decode_tps', 'client_ttft_s', 'client_total_s'):
            baseline = [row['baseline'][key] for row in blocks]
            candidate = [row['candidate'][key] for row in blocks]
            if any(value is None or not math.isfinite(value) or value <= 0 for value in baseline + candidate):
                raise ValueError(f'invalid {key} observations')
            ratios = [b / a for a, b in zip(baseline, candidate)]
            result[key] = {'baseline_median': statistics.median(baseline),
                           'candidate_median': statistics.median(candidate),
                           'median_within_block_candidate_over_baseline': statistics.median(ratios),
                           'paired_bootstrap_95_interval': interval(ratios)}
        summaries.append(result)
    return {'scope': 'same-source stability controls; no optimization speedup claim',
            'uncertainty': 'bootstrap whole independent paired processes; three pairs are screening, not confirmation',
            'stage_time_scope': 'engine DONE times exposed through metrics; preserve engine reporting precision',
            'ttft_scope': 'client first nonempty content/reasoning delta; SSE chunks need not equal tokens',
            'clock_scope': 'dynamic; missing frequency samples remain explicit',
            'planned_blocks': plan['planned_blocks'], 'cells': summaries, 'raw_paired_blocks': dict(records), 'rejected_or_incomplete': rejected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--clock-samples', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.campaign, args.clock_samples)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    with (args.output / 'summary.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['cell', 'paired_blocks', 'variant', 'median_prompt_tps', 'median_decode_tps', 'median_client_ttft_s', 'median_client_total_s'])
        for row in result['cells']:
            for variant in ('baseline', 'candidate'):
                writer.writerow([row['cell'], row['paired_blocks'], variant] + [row[key][variant + '_median'] for key in ('prompt_tps', 'decode_tps', 'client_ttft_s', 'client_total_s')])
    print(json.dumps(result['cells'], indent=2))


if __name__ == '__main__':
    main()
