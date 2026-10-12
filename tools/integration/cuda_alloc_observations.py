"""Summarize CUDA runtime allocation-interposer records by process."""
import argparse
import json
from pathlib import Path

PREFIX = 'CUDA_ALLOC_PROBE '
OPS = {'malloc', 'free'}


def summarize(lines, labels=None):
    labels = labels or {}
    processes = {}
    for line in lines:
        if PREFIX not in line:
            continue
        row = json.loads(line.split(PREFIX, 1)[1])
        pid, op = row.get('pid'), row.get('op')
        if not isinstance(pid, int) or pid <= 0 or op not in OPS:
            raise ValueError('invalid CUDA allocation event identity')
        for field in ('bytes', 'status', 'current_bytes', 'high_bytes'):
            if not isinstance(row.get(field), int) or row[field] < 0:
                raise ValueError(f'invalid CUDA allocation event field: {field}')
        if row['high_bytes'] < row['current_bytes']:
            raise ValueError('CUDA allocation high-water mark is below current bytes')

        proc = processes.setdefault(pid, {
            'events': 0, 'allocation_events': 0, 'free_events': 0,
            'failed_events': 0, 'cuda_runtime_highwater_bytes': 0,
            'last_current_bytes': 0,
        })
        if row['high_bytes'] < proc['cuda_runtime_highwater_bytes']:
            raise ValueError(f'CUDA allocation high-water mark regressed for pid {pid}')
        proc['events'] += 1
        proc['allocation_events'] += op == 'malloc'
        proc['free_events'] += op == 'free'
        proc['failed_events'] += row['status'] != 0
        proc['cuda_runtime_highwater_bytes'] = row['high_bytes']
        proc['last_current_bytes'] = row['current_bytes']

    if not processes:
        raise ValueError('no CUDA_ALLOC_PROBE records found')
    return {
        'scope': 'cudaMalloc/cudaMallocManaged/cudaFree interposition only; requested bytes per process, not physical backing or total board memory',
        'processes': [dict(pid=pid, **({'label': labels[pid]} if pid in labels else {}),
                           **processes[pid]) for pid in sorted(processes)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-log', type=Path, required=True,
                        help='combined log containing CUDA_ALLOC_PROBE records')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--label', action='append', default=[], metavar='PID=NAME',
                        help='optional process label; repeat for multiple processes')
    args = parser.parse_args()
    labels = {}
    for item in args.label:
        try:
            pid_text, label = item.split('=', 1)
            pid = int(pid_text)
        except ValueError as exc:
            parser.error(f'invalid process label {item!r}; expected PID=NAME')
        if pid <= 0 or not label or pid in labels:
            parser.error(f'invalid or duplicate process label {item!r}')
        labels[pid] = label
    result = summarize(args.engine_log.read_text().splitlines(), labels)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
