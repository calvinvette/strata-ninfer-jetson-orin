"""Summarize opt-in owner events; requested payloads are not physical RAM totals."""
import argparse
import json
from pathlib import Path

PREFIX = 'strata integration: '


def summarize(lines):
    live, peaks, current, graphs, views, payloads, reservations = {}, {}, {}, {}, {}, {}, {}
    allocations = frees = 0
    for line in lines:
        if not line.startswith(PREFIX):
            continue
        row = json.loads(line[len(PREFIX):])
        if row.get('schema') != 1:
            raise ValueError('unsupported owner event schema')
        owner = (row['owner'], row['instance'], row['device'])
        key = (row['device'], row['allocation'])
        if row['kind'] == 'reservation':
            size = row['requested_bytes']
            if not isinstance(size, int) or size <= 0 or row['allocation'] != 0 or row['count'] != 0:
                raise ValueError('invalid planned reservation event')
            if owner in reservations:
                raise ValueError('duplicate planned reservation label for one instance/device')
            reservations[owner] = size
        elif row['kind'] == 'allocate':
            size = row['requested_bytes']
            if not isinstance(size, int) or size <= 0 or not key[1] or key in live:
                raise ValueError('invalid or duplicate allocation event')
            live[key] = (owner, size)
            current[owner] = current.get(owner, 0) + size
            peaks[owner] = max(peaks.get(owner, 0), current[owner])
            allocations += 1
        elif row['kind'] == 'free':
            if key not in live or live[key][0] != owner:
                raise ValueError('unmatched free or conflicting allocation owner')
            current[owner] -= live.pop(key)[1]
            frees += 1
        elif row['kind'] == 'graph_instantiate':
            if row['count'] != 1 or row['requested_bytes']:
                raise ValueError('invalid graph instantiation observation')
            graphs[owner] = graphs.get(owner, 0) + 1
        elif row['kind'] == 'view':
            if row['count'] != 1 or row['requested_bytes'] <= 0 or not key[1]:
                raise ValueError('invalid borrowed/alias view observation')
            # Views may overlap or be relaid out repeatedly. Never add their
            # bytes to observed allocation ownership or infer parent backing.
            views[owner] = views.get(owner, 0) + 1
        elif row['kind'] == 'payload_snapshot':
            if row['allocation'] or row['count'] or row['requested_bytes'] < 0:
                raise ValueError('invalid owner payload snapshot')
            payloads[owner] = row['requested_bytes']
        else:
            raise ValueError('unknown owner event kind')
    if not allocations:
        raise ValueError('no observed allocations; tracing absent or unsupported')
    owners = sorted(set(current) | set(graphs) | set(views) | set(payloads))
    return {
        'scope': 'observed sites only; requested payload bytes, not physical backing or total process ownership',
        'coverage': 'instrumented CUDA/HIP ordinary ExpertCache single-block backing, CUDA segmented ExpertCache mapped VMM physical segments, pageable/pinned expert-stage host buffers, primary SessionState backing, verifier primary arena/window graphs, prefill-owned vector allocations/views and MTP state/scratch arenas; shared KV VMM pools, SYCL ExpertCache, stage/batch sessions and other sites excluded',
        'graph_bytes': 'unsupported; counts do not measure driver or graph-pool bytes',
        'cleanup': 'live at log end is not a leak verdict; process termination may bypass destructors',
        'allocation_events': allocations, 'free_events': frees,
        'planned_reservations': {
            'scope': 'cache-sizing budget holds only; metadata, not allocated/physical bytes and never added to allocation totals',
            'events': [{'label': o[0], 'instance': o[1], 'device': o[2], 'bytes': b}
                       for o, b in sorted(reservations.items())]},
        'owners': [{'owner': o[0], 'instance': o[1], 'device': o[2],
                    'peak_observed_requested_bytes': peaks.get(o, 0),
                    'live_observed_requested_bytes': current.get(o, 0),
                    'view_events': views.get(o, 0),
                    'last_owner_reported_payload_bytes': payloads.get(o),
                    'successful_graph_instantiations': graphs.get(o, 0)} for o in owners]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.engine_log.read_text().splitlines())
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
