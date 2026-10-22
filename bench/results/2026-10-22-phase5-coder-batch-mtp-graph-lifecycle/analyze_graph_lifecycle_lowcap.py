#!/usr/bin/env python3
"""Verify observed batch graph eviction followed by layout recapture."""
import json
from collections import Counter
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run-graph-lifecycle-recapture'
log = (RUN / 'batch-mtp.log').read_text(errors='replace')
events = re.finditer(r'captured the batch window over slots ([0-9,]+)|'
                     r'evicted least-recently-used batch graph layout', log)
seen_at = {}
evictions = 0
recaptures = []
layouts = []
for event in events:
    layout = event.group(1)
    if layout is None:
        evictions += 1
    else:
        layouts.append(layout)
        if layout in seen_at and evictions > seen_at[layout]:
            recaptures.append({'layout': layout, 'after_eviction_count': evictions})
        seen_at[layout] = evictions

supervisor = json.loads((ROOT / 'supervisor-graph-lifecycle-recapture/result.json').read_text())
samples = [json.loads(line) for line in (ROOT / 'supervisor-graph-lifecycle-recapture/memory.jsonl').read_text().splitlines() if line.strip()]
event_maxima = {}
for sample in samples:
    for cg in sample.get('cgroups', []):
        if cg.get('path', '').endswith('.scope'):
            for name, value in cg.get('memory_events', {}).items():
                event_maxima[name] = max(event_maxima.get(name, 0), value)
run = json.loads((RUN / 'result.json').read_text())
analysis = {
    'purpose': 'opt-in batch-MTP graph-pool eviction and recapture stress; not a speed comparison',
    'profile': run['profile'],
    'status': supervisor['status'],
    'minimum_available_gib': supervisor['minimum_available_bytes'] / 2**30,
    'minimum_admission_gib': supervisor['minimum_admission_available_bytes'] / 2**30,
    'memory_samples': len(samples),
    'cgroup_memory_event_maxima': event_maxima,
    'submitted_requests_completed': len(run['batch_mtp']),
    'tokens_per_request': {name: len(result['tokens']) for name, result in run['batch_mtp'].items()},
    'batch_windows': int(re.search(r'strata batch: (\d+) windows', log).group(1)),
    'captured_layouts': len(layouts),
    'distinct_layout_keys': dict(Counter(layouts)),
    'evictions': evictions,
    'recaptures_after_eviction': recaptures,
    'graph_lifecycle_pass': supervisor['status'] == 'pass' and bool(recaptures) and
                            len(run['batch_mtp']) == 8 and all(len(v['tokens']) == 6
                                                               for v in run['batch_mtp'].values()),
    'limits': ['The cap was deliberately set to 1 via STRATA_BATCH_MTP_GRAPH_LIMIT; default remains 64.',
               'No graph-pool speed or default-cap performance claim.',
               'HIP/SYCL build not yet complete because maestro1 has no free filesystem space.'],
}
(ROOT / 'graph-lifecycle-lowcap-analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
print(json.dumps(analysis, indent=2))
if not analysis['graph_lifecycle_pass']:
    raise SystemExit(1)
