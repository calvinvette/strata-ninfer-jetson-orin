"""Run one explicit control command with durable physical-memory telemetry.

No engine flags are inferred from campaign.json. This Linux supervisor is an
integration harness, not a second runtime allocation ledger. Stdlib only.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time

GIB = 1024 ** 3


def process_snapshot(group_id):
    processes = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            # comm can contain spaces or parentheses; fields follow its last ')'.
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) != group_id:
                continue
            io = {}
            for line in (entry / 'io').read_text().splitlines():
                key, value = line.split(':')
                io[key] = int(value)
            processes.append({'pid': int(entry.name), 'rss_bytes': int(fields[21]) * os.sysconf('SC_PAGE_SIZE'),
                              'minor_faults': int(fields[7]), 'major_faults': int(fields[9]),
                              'io': io})
        except (OSError, ValueError, IndexError):
            continue  # process exited while sampled
    return {'process_group': processes,
            'process_group_rss_bytes': sum(p['rss_bytes'] for p in processes),
            'rss_scope': 'CPU RSS only; never total GPU-inclusive physical use',
            'host_diskstats': Path('/proc/diskstats').read_text()}


def memory_snapshot(proc_root=Path('/proc'), cgroup_root=Path('/sys/fs/cgroup')):
    mem = {}
    for line in (proc_root / 'meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        mem[key] = int(value.split()[0]) * 1024
    limits = []
    # cgroup v2: every ancestor can be the limiting constraint.
    for line in (proc_root / 'self/cgroup').read_text().splitlines():
        if line.startswith('0::'):
            node = cgroup_root / line[3:].lstrip('/')
            while True:
                try:
                    current = int((node / 'memory.current').read_text())
                    maximum = (node / 'memory.max').read_text().strip()
                    limits.append({'path': str(node), 'current_bytes': current,
                                   'max_bytes': None if maximum == 'max' else int(maximum)})
                except FileNotFoundError:
                    pass
                if node == cgroup_root:
                    break
                if cgroup_root not in node.parents:
                    raise ValueError('cgroup path outside root')
                node = node.parent
    remaining = [max(0, x['max_bytes'] - x['current_bytes']) for x in limits
                 if x['max_bytes'] is not None]
    return {'monotonic_s': time.monotonic(), 'wall_time_s': time.time(),
            'available_bytes': mem['MemAvailable'], 'total_bytes': mem['MemTotal'],
            'swap_used_bytes': mem['SwapTotal'] - mem['SwapFree'],
            'cgroups': limits, 'cgroup_v2_observed': bool(limits),
            'admission_available_bytes': min([mem['MemAvailable']] + remaining)}


def stop_group(child, grace_s):
    """Kill remaining descendants even if the group leader has already exited."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline:
        child.poll()
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=5)


def write_result(path, result):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def run(command, output, *, floor_bytes=6 * GIB, interval_s=1, timeout_s=3600,
        grace_s=3, sample=memory_snapshot, lock_path=None):
    if not command or floor_bytes < 6 * GIB or min(interval_s, timeout_s, grace_s) <= 0:
        raise ValueError('explicit command, >=6 GiB floor and positive timing limits required')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {'command': command, 'cwd': os.getcwd(), 'status': 'not_run',
              'floor_bytes': floor_bytes, 'started_wall_s': time.time(),
              'energy_scope': 'not measured; raw tegrastats rails only',
              'counters': 'engine stdout/stderr; unavailable counters are not inferred'}
    child = telemetry = None
    caught = []
    previous = {}
    lock_path = lock_path or Path('/tmp') / f'strata-integration-{os.getuid()}.lock'
    with Path(lock_path).open('a') as lock, (output / 'memory.jsonl').open('w') as samples:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            initial = sample()
            result['initial_memory'] = initial
            if initial['admission_available_bytes'] < floor_bytes:
                result.update(status='pressure_abort', reason='prelaunch physical/cgroup headroom')
                return result
            for sig in (signal.SIGTERM, signal.SIGINT):
                previous[sig] = signal.signal(sig, lambda number, frame: caught.append(number))
            with (output / 'stdout.txt').open('w') as stdout, (output / 'stderr.txt').open('w') as stderr, (output / 'tegrastats.txt').open('w') as rails:
                try:
                    telemetry = subprocess.Popen(['tegrastats', '--interval', str(max(100, int(interval_s * 1000)))], stdout=rails, stderr=subprocess.STDOUT, start_new_session=True)
                    result['tegrastats'] = 'started; inspect raw log for availability'
                except FileNotFoundError:
                    result['tegrastats'] = 'unsupported: executable absent'
                child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
                result.update(status='not_run', reason='running; incomplete until terminal result')
                write_result(output / 'result.json', result)
                start = time.monotonic()
                while True:
                    row = sample()
                    row.update(process_snapshot(child.pid))
                    samples.write(json.dumps(row) + '\n')
                    samples.flush()
                    os.fsync(samples.fileno())
                    result['minimum_available_bytes'] = min(result.get('minimum_available_bytes', initial['available_bytes']), row['available_bytes'])
                    if row['admission_available_bytes'] < floor_bytes:
                        result.update(status='pressure_abort', reason='physical/cgroup headroom during execution')
                        break
                    if caught:
                        result.update(status='fail', reason=f'supervisor signal {caught[0]}')
                        break
                    if time.monotonic() - start > timeout_s:
                        result.update(status='fail', reason='timeout')
                        break
                    code = child.poll()
                    if code is not None:
                        result.update(status='pass' if code == 0 else 'fail', returncode=code,
                                      reason='command exit; numerical/workload qualification is separate')
                        break
                    time.sleep(interval_s)
                result['elapsed_s'] = time.monotonic() - start
        except BlockingIOError:
            result.update(status='not_run', reason='another integration command holds the board lock')
        except Exception as exc:
            result.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
        finally:
            for process in (child, telemetry):
                if process is not None:
                    try:
                        stop_group(process, grace_s)
                    except Exception as exc:
                        result.update(status='fail', reason=f'cleanup failed: {exc}')
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            result['finished_wall_s'] = time.time()
            write_result(output / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=3600)
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--term-grace', type=float, default=3)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    result = run(command, args.output, interval_s=args.interval, timeout_s=args.timeout, grace_s=args.term_grace)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
