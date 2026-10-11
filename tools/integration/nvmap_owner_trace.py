"""Sample the Linux Tegra NVMap IOVMM client totals as JSONL.

Run with sufficient privilege to read /sys/kernel/debug/nvmap/iovmm/clients.
This is a platform owner counter, not a substitute for host physical-memory
headroom or cgroup admission accounting.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time

SIZE = re.compile(r'^(\d+(?:\.\d+)?)([KMG]?)$')


def parse_size_bytes(value: str) -> int:
    match = SIZE.fullmatch(value)
    if not match:
        raise ValueError(f'invalid NVMap size: {value!r}')
    scale = {'': 1, 'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3}[match.group(2)]
    return int(float(match.group(1)) * scale)


def parse_clients(text: str) -> list[dict]:
    clients = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0] == 'CLIENT' or fields[0] == 'total':
            continue
        try:
            pid = int(fields[-2])
            size_bytes = parse_size_bytes(fields[-1])
        except ValueError:
            continue
        clients.append({'client': fields[0], 'process': ' '.join(fields[1:-2]),
                        'pid': pid, 'size_bytes': size_bytes})
    return clients


def sample(clients_path: Path) -> dict:
    clients = parse_clients(clients_path.read_text())
    return {'monotonic_s': time.monotonic(), 'wall_time_s': time.time(),
            'clients': clients, 'reported_client_bytes': sum(x['size_bytes'] for x in clients)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--duration', type=float, default=60.0)
    parser.add_argument('--interval', type=float, default=0.1)
    parser.add_argument('--clients-path', type=Path,
                        default=Path('/sys/kernel/debug/nvmap/iovmm/clients'))
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error('duration and interval must be positive')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.duration
    with args.output.open('w') as stream:
        while time.monotonic() < deadline:
            stream.write(json.dumps(sample(args.clients_path), sort_keys=True) + '\n')
            stream.flush()
            time.sleep(args.interval)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
