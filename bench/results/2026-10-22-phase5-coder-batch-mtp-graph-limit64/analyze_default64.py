#!/usr/bin/env python3
"""Audit default batch-MTP graph-cap eviction and physical-memory telemetry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

GIB = 1024 ** 3
CAPTURE = re.compile(r'captured the batch window over slots ([0-9,]+)')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root
    run = json.loads((root / 'run/result.json').read_text())
    supervisor = json.loads((root / 'supervisor/result.json').read_text())
    log = (root / 'run/batch-mtp-engine.log').read_text(errors='replace')
    captures = CAPTURE.findall(log)
    unique = set(captures)
    evictions = log.count('evicted least-recently-used batch graph layout')
    cap_lines = re.findall(r'batch-MTP graph layout limit (\d+)([^\n]*)', log)
    events = {'low': 0, 'high': 0, 'max': 0, 'oom': 0, 'oom_kill': 0, 'oom_group_kill': 0}
    scoped_memory_samples = 0
    minimum_available = 2**63 - 1
    minimum_admission = 2**63 - 1
    for line in (root / 'supervisor/memory.jsonl').read_text().splitlines():
        row = json.loads(line)
        minimum_available = min(minimum_available, row['available_bytes'])
        minimum_admission = min(minimum_admission, row['admission_available_bytes'])
        scope = next((cg for cg in row.get('cgroups', []) if cg.get('max_bytes') is not None), None)
        if scope is None:
            continue
        scoped_memory_samples += 1
        for key in events:
            events[key] = max(events[key], scope.get('memory_events', {}).get(key, 0))

    eviction_lines = [i for i, line in enumerate(log.splitlines())
                      if 'evicted least-recently-used batch graph layout' in line]
    log_lines = log.splitlines()
    first_eviction_unique = None
    if eviction_lines:
        first = eviction_lines[0]
        first_eviction_unique = len(set(
            key for line in log_lines[:first]
            if (match := CAPTURE.search(line)) is not None
            for key in [match.group(1)]))
    checks = {
        'supervisor_passed': supervisor.get('status') == 'pass' and supervisor.get('returncode') == 0,
        'all_requests_completed': run.get('requests_completed') == run.get('requests_submitted'),
        'default_limit_64_logged': any(value == '64' and not suffix for value, suffix in cap_lines),
        'more_than_64_unique_layouts': len(unique) > 64,
        'first_eviction_after_64_layouts': first_eviction_unique == 64,
        'eviction_observed': evictions > 0,
        'six_gib_headroom_preserved': minimum_available >= 6 * GIB and minimum_admission >= 6 * GIB,
        'zero_cgroup_pressure_or_oom_events': all(value == 0 for value in events.values()),
    }
    result = {
        'passed': all(checks.values()),
        'checks': checks,
        'requests_submitted': run.get('requests_submitted'),
        'requests_completed': run.get('requests_completed'),
        'graph_limit_log': cap_lines,
        'graph_capture_count': len(captures),
        'unique_layout_count': len(unique),
        'eviction_count': evictions,
        'first_eviction_after_unique_layouts': first_eviction_unique,
        'duplicate_capture_count': len(captures) - len(unique),
        'minimum_host_available_gib': minimum_available / GIB,
        'minimum_admission_available_gib': minimum_admission / GIB,
        'supervisor_samples': scoped_memory_samples,
        'maximum_cgroup_memory_events': events,
    }
    destination = args.output or (root / 'analysis.json')
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
