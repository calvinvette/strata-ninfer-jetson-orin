"""Calibrate cgroup-v2 read-byte accounting with an O_DIRECT file read."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def cgroup_scope(proc_cgroup: str, root: Path = Path('/sys/fs/cgroup')) -> Path:
    for line in proc_cgroup.splitlines():
        hierarchy, _controllers, path = line.split(':', 2)
        if hierarchy == '0':
            return root / path.lstrip('/')
    raise ValueError('unified cgroup-v2 membership not found')


def io_stat(path: Path) -> dict[str, dict[str, int]]:
    result = {}
    for line in path.read_text().splitlines():
        device, *fields = line.split()
        result[device] = {key: int(value) for key, value in
                          (field.split('=', 1) for field in fields)}
    return result


def read_byte_deltas(before: dict[str, dict[str, int]],
                     after: dict[str, dict[str, int]]) -> dict[str, int]:
    devices = before.keys() | after.keys()
    return {device: after.get(device, {}).get('rbytes', 0) -
            before.get(device, {}).get('rbytes', 0) for device in devices}


def calibrate(source: Path, byte_count: int, *, cgroup: Path | None = None) -> dict:
    source = source.resolve()
    if byte_count <= 0 or byte_count % (4 * 1024 * 1024):
        raise ValueError('byte count must be a positive multiple of 4 MiB')
    if source.stat().st_size < byte_count:
        raise ValueError('source file is smaller than requested calibration read')
    cgroup = cgroup or cgroup_scope(Path('/proc/self/cgroup').read_text())
    stat_path = cgroup / 'io.stat'
    if not stat_path.is_file():
        raise OSError(f'cgroup I/O accounting is unavailable: {stat_path}')
    major, minor = os.major(source.stat().st_dev), os.minor(source.stat().st_dev)
    device = f'{major}:{minor}'
    before = io_stat(stat_path)
    command = ['dd', f'if={source}', 'of=/dev/null', 'iflag=direct',
               'bs=4M', f'count={byte_count // (4 * 1024 * 1024)}', 'status=none']
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    after = io_stat(stat_path)
    deltas = read_byte_deltas(before, after)
    positive_deltas = {key: value for key, value in deltas.items() if value > 0}
    delta = sum(positive_deltas.values())
    return {
        'scope': str(cgroup), 'source': str(source),
        'source_device': device, 'requested_bytes': byte_count,
        'read_bytes_delta_by_device': positive_deltas,
        'read_bytes_delta_scope_total': delta,
        'command': command, 'returncode': completed.returncode,
        'passed': delta >= byte_count,
        'interpretation': 'sum of positive cgroup-subtree block-device deltas; calibration only, not request attribution',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', type=Path, required=True)
    parser.add_argument('--bytes', type=int, default=64 * 1024 * 1024)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = calibrate(args.path, args.bytes)
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end='')
    if not result['passed']:
        raise SystemExit('cgroup read-byte delta did not account for the direct read')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
