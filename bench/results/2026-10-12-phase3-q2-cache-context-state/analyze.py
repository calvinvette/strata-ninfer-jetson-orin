"""Validate and summarize the cache/context state matrix outputs."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from compare_gdn_state_dumps import compare

STATE_RE = re.compile(r'STATE_HASH L=511 (.+)$')


def state_hashes(log):
    rows = [STATE_RE.search(line) for line in log.read_text(errors='replace').splitlines()]
    found = [row.group(1) for row in rows if row]
    if len(found) != 1:
        raise ValueError(f'{log}: expected one L=511 state fingerprint, found {len(found)}')
    fields = {}
    for token in found[0].split():
        key, value = token.split('=', 1)
        fields[key] = value
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    campaign_path = args.campaign.resolve()
    campaign = json.loads(campaign_path.read_text())
    root = campaign_path.parent
    rows = campaign['runs']
    if len(rows) != 12 or any(row['status'] != 'pass' for row in rows):
        raise ValueError('expected twelve passed matrix runs')
    grouped = {}
    observed_min = None
    for row in rows:
        run = root / 'runs' / row['name']
        workload = json.loads((run / 'workload.json').read_text())
        supervisor = json.loads((run / 'supervisor/result.json').read_text())
        owner = json.loads((run / 'owner-summary.json').read_text())
        if supervisor['status'] != 'pass' or supervisor['minimum_available_bytes'] < campaign['floor_bytes']:
            raise ValueError(f"{row['name']}: supervisor failed or crossed the memory floor")
        if workload['engine_sha256'] != campaign['engine_sha256']:
            raise ValueError(f"{row['name']}: engine identity differs")
        if workload['generated_ids'] != [271] or workload['prompt_tokens'] != 511:
            raise ValueError(f"{row['name']}: request output or token count differs")
        fields = state_hashes(run / 'engine.log')
        key = (row['cache_budget'], row['context_tokens'])
        grouped.setdefault(key, []).append({
            'name': row['name'], 'repetition': row['repetition'],
            'gdn_dump_sha256': workload['gdn_dump_sha256'],
            'state_hashes': fields,
            'hits': workload['usage'].get('hits'),
            'lookups': workload['usage'].get('lookups'),
            'minimum_available_bytes': supervisor['minimum_available_bytes'],
            'owner_allocation_events': owner['allocation_events'],
            'owner_free_events': owner['free_events'],
            'owner_live_requested_bytes': owner['observed_allocation_bytes_by_device']['live_at_log_end'],
        })
        observed_min = min(observed_min or supervisor['minimum_available_bytes'],
                           supervisor['minimum_available_bytes'])

    cells = []
    for (cache, context), samples in sorted(grouped.items()):
        for sample in samples[1:]:
            if sample['gdn_dump_sha256'] != samples[0]['gdn_dump_sha256']:
                raise ValueError(f'GDN state was not repeatable at cache={cache}, context={context}')
            if sample['state_hashes'] != samples[0]['state_hashes']:
                raise ValueError(f'accepted-prefix fingerprint was not repeatable at cache={cache}, context={context}')
        if len({sample['hits'] for sample in samples}) != 1 or len({sample['lookups'] for sample in samples}) != 1:
            raise ValueError(f'expert hit counts varied at cache={cache}, context={context}')
        cells.append({
            'cache_budget': cache, 'context_tokens': context,
            'repetitions': len(samples), 'gdn_dump_sha256': samples[0]['gdn_dump_sha256'],
            'state_hashes': samples[0]['state_hashes'],
            'hits': samples[0]['hits'], 'lookups': samples[0]['lookups'],
            'minimum_available_bytes': min(s['minimum_available_bytes'] for s in samples),
            'owner_event_counts': sorted({(s['owner_allocation_events'], s['owner_free_events']) for s in samples}),
            'samples': samples,
        })

    by_key = {(cell['cache_budget'], cell['context_tokens']): cell for cell in cells}
    contexts = campaign['context_values']
    caches = campaign['cache_values']
    context_equal = {}
    for cache in caches:
        first, second = (by_key[(cache, context)] for context in contexts)
        context_equal[str(cache)] = {
            'gdn_dump_identical': first['gdn_dump_sha256'] == second['gdn_dump_sha256'],
            'all_accepted_prefix_hashes_identical': first['state_hashes'] == second['state_hashes'],
        }
    cache_equal = {}
    for context in contexts:
        first, second = (by_key[(cache, context)] for cache in caches)
        cache_equal[str(context)] = {
            'gdn_dump_identical': first['gdn_dump_sha256'] == second['gdn_dump_sha256'],
            'all_accepted_prefix_hashes_identical': first['state_hashes'] == second['state_hashes'],
        }

    ref = ROOT / 'build/integration/q2-cache-context-state' / f"rep-00-cache-{caches[0]}-context-{contexts[0]}" / 'gdn-L511.bin'
    cand = ROOT / 'build/integration/q2-cache-context-state' / f"rep-00-cache-{caches[1]}-context-{contexts[0]}" / 'gdn-L511.bin'
    numeric = compare(ref, cand)
    result = {
        'schema': 1,
        'engine_sha256': campaign['engine_sha256'],
        'prompt_tokens': 511,
        'prompt_sha256': rows[0]['prompt_sha256'],
        'generated_ids': [271],
        'repetitions_per_cell': campaign['repetitions'],
        'minimum_host_available_bytes': observed_min,
        'cache_context_cells': cells,
        'same_cache_across_context': context_equal,
        'same_context_across_cache': cache_equal,
        'one_cross_cache_gdn_comparison_at_first_context': numeric,
        'scope': 'correctness/state/admission only; no timing or quality claim',
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'cells': len(cells), 'minimum_host_available_bytes': observed_min,
        'same_cache_across_context': context_equal,
        'same_context_across_cache': cache_equal,
        'cross_cache_global_relative_l2': numeric['global_relative_l2'],
        'different_floats': numeric['different_floats'],
    }, indent=2))


if __name__ == '__main__':
    main()
