"""Audit a completed MTP x KV x workload screen for residency-matched timings."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from mtp_kv_workload_screen import bootstrap_interval

METRICS = ('prompt_tps', 'decode_tps', 'client_ttft_s', 'client_total_s')


def residency(row):
    engine = row.get('engine', {})
    return engine.get('expert_slots'), engine.get('expert_cache_mib')


def make_pair(rows, block, kv, workload, window):
    control = rows.get((block, kv, workload, 0))
    candidate = rows.get((block, kv, workload, window))
    if control is None or candidate is None:
        return None, 'missing arm'
    if control.get('status') != 'pass' or candidate.get('status') != 'pass':
        return None, 'arm did not pass'
    if residency(control) != residency(candidate):
        return None, f'residency mismatch {residency(control)} != {residency(candidate)}'
    control_day, candidate_day = control.get('local_run_date'), candidate.get('local_run_date')
    if not control_day or not candidate_day:
        return None, 'arm local start date unavailable'
    if control_day != candidate_day:
        return None, f'not a same-local-day pair: {control_day} != {candidate_day}'
    cm, tm = control.get('metrics', {}), candidate.get('metrics', {})
    if cm.get('prompt_tokens') != tm.get('prompt_tokens'):
        return None, 'actual prompt-token count mismatch'
    if control.get('engine', {}).get('kv') != kv or candidate.get('engine', {}).get('kv') != kv:
        return None, 'engine KV format mismatch'
    pair = {'block': block, 'kv': kv, 'workload': workload,
            'expert_slots': residency(control)[0], 'expert_cache_mib': residency(control)[1],
            'local_run_date': control_day}
    for metric in METRICS:
        a, b = cm.get(metric), tm.get(metric)
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or a <= 0 or b <= 0:
            return None, f'invalid metric {metric}'
        pair[metric + '_ratio'] = b / a
    return pair, None


def audit(campaign, seed=20261023, run_root=None):
    enriched = []
    for record in campaign['runs']:
        row = dict(record)
        if run_root is not None and 'directory' in row:
            result_path = Path(run_root) / row['directory'] / 'supervisor/result.json'
            if result_path.exists():
                supervisor = json.loads(result_path.read_text())
                started = supervisor.get('started_wall_s')
                if isinstance(started, (int, float)):
                    row['local_run_date'] = datetime.fromtimestamp(started).date().isoformat()
                    row['supervisor_started_wall_s'] = started
        enriched.append(row)
    rows = {(r['block'], r['kv'], r['workload'], r['window']): r
            for r in enriched if 'block' in r}
    blocks = sorted({r['block'] for r in enriched if 'block' in r})
    kvs = campaign['kv_formats']
    workloads = campaign['workloads']
    window = max(campaign['mtp_windows'])
    pairs, exclusions = [], []
    by_cell = {}
    for block in blocks:
        for kv in kvs:
            for workload in workloads:
                pair, reason = make_pair(rows, block, kv, workload, window)
                key = (block, kv, workload)
                by_cell[key] = pair
                entry = {'block': block, 'kv': kv, 'workload': workload}
                if reason:
                    c, t = rows.get((block, kv, workload, 0)), rows.get((block, kv, workload, window))
                    entry.update(qualified=False, reason=reason,
                                 control_residency=residency(c) if c else None,
                                 candidate_residency=residency(t) if t else None)
                    exclusions.append(entry)
                else:
                    pair['qualified'] = True
                    pairs.append(pair)

    cell_effects = []
    for kv in kvs:
        for workload in workloads:
            selected = [by_cell[(b, kv, workload)] for b in blocks if by_cell[(b, kv, workload)]]
            item = {'kv': kv, 'workload': workload, 'paired_blocks': len(selected),
                    'paired_block_ids': [p['block'] for p in selected]}
            for metric in METRICS:
                vals = [p[metric + '_ratio'] for p in selected]
                item[metric + '_effect_percent'] = (statistics.median(vals) - 1) * 100 if vals else None
                interval = bootstrap_interval(vals, seed + len(cell_effects) * 101 + len(metric))
                item[metric + '_paired_bootstrap_95_interval_percent'] = [
                    (x - 1) * 100 if x is not None else None for x in interval]
                item[metric + '_paired_ratios'] = vals
            cell_effects.append(item)

    kv_interactions, workload_interactions, three_way = [], [], []
    for block in blocks:
        for workload in workloads:
            a, b = (by_cell[(block, kv, workload)] for kv in kvs)
            item = {'block': block, 'workload': workload, 'qualified': False}
            if (a and b and a['local_run_date'] == b['local_run_date'] and
                    (a['expert_slots'], a['expert_cache_mib']) == (b['expert_slots'], b['expert_cache_mib'])):
                item['qualified'] = True
                item['expert_slots'] = a['expert_slots']
                for metric in METRICS:
                    item[metric + '_int8_vs_fp16_interaction_percent'] = (b[metric + '_ratio'] / a[metric + '_ratio'] - 1) * 100
            else:
                item['reason'] = 'missing residency-matched MTP pair or KV capacities differ'
            kv_interactions.append(item)
        if len(workloads) >= 2:
            for kv in kvs:
                a, b = (by_cell[(block, kv, workload)] for workload in workloads)
                item = {'block': block, 'kv': kv, 'qualified': False}
                if (a and b and a['local_run_date'] == b['local_run_date'] and
                        (a['expert_slots'], a['expert_cache_mib']) == (b['expert_slots'], b['expert_cache_mib'])):
                    item['qualified'] = True
                    item['expert_slots'] = a['expert_slots']
                    for metric in METRICS:
                        item[metric + '_long_vs_short_interaction_percent'] = (b[metric + '_ratio'] / a[metric + '_ratio'] - 1) * 100
                else:
                    item['reason'] = 'missing residency-matched MTP pair or prompt-cell capacities differ'
                workload_interactions.append(item)
            all_cells = [by_cell[(block, kv, workload)] for kv in kvs for workload in workloads]
            qualified = (all(p is not None for p in all_cells) and
                         len({(p['expert_slots'], p['expert_cache_mib']) for p in all_cells}) == 1 and
                         len({p['local_run_date'] for p in all_cells}) == 1)
            item = {'block': block, 'qualified': qualified}
            if qualified:
                for metric in METRICS:
                    fp_short = by_cell[(block, kvs[0], workloads[0])][metric + '_ratio']
                    fp_long = by_cell[(block, kvs[0], workloads[1])][metric + '_ratio']
                    int_short = by_cell[(block, kvs[1], workloads[0])][metric + '_ratio']
                    int_long = by_cell[(block, kvs[1], workloads[1])][metric + '_ratio']
                    item[metric + '_three_way_interaction_percent'] = ((int_long / fp_long) / (int_short / fp_short) - 1) * 100
            else:
                item['reason'] = 'not all eight arms passed at identical expert residency'
            three_way.append(item)

    return {'schema': 2, 'source_campaign': str(campaign.get('source_commit')),
            'qualification_rule': 'timing pairs require passing arms from the same local calendar day, matching KV, actual prompt token count, and identical expert slots/cache MiB; higher interactions require matching residency and date across all contributing cells',
            'cell_effects': cell_effects, 'qualified_cell_pairs': pairs,
            'excluded_cell_pairs': exclusions,
            'mtp_by_kv_interactions': kv_interactions,
            'mtp_by_workload_interactions': workload_interactions,
            'three_way_interactions': three_way}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('campaign', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--run-root', type=Path,
                        help='campaign directory containing per-arm supervisor results; required to check paired dates')
    args = parser.parse_args()
    campaign = json.loads(args.campaign.read_text())
    result = audit(campaign, campaign.get('seed', 0), args.run_root or args.campaign.parent)
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
