"""Read observed CPU/GPU/EMC frequencies; never set clocks or power mode."""
import argparse
import json
from pathlib import Path
import subprocess
import time

EMC = '/sys/kernel/debug/bpmp/debug/clk/emc/rate'
GPU = '/sys/class/devfreq/17000000.gpu/cur_freq'


def read_hz(path, scale=1):
    try:
        return {'hz': int(Path(path).read_text()) * scale, 'path': str(path)}
    except (OSError, ValueError) as exc:
        return {'status': 'unsupported', 'path': str(path), 'reason': str(exc)}


def snapshot(privileged_emc=False):
    emc = read_hz(EMC)
    if 'hz' not in emc and privileged_emc:
        result = subprocess.run(['sudo', '-n', 'cat', EMC], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            emc = {'hz': int(result.stdout), 'path': EMC, 'access': 'read-only sudo -n cat'}
        else:
            emc['reason'] = result.stderr.strip()
    cpu = {p.parent.parent.name: read_hz(p, 1000) for p in
           Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq')}
    return {'wall_time_s': time.time(), 'monotonic_s': time.monotonic(),
            'cpu': cpu, 'gpu': read_hz(GPU), 'emc': emc,
            'clock_control': 'none; observed dynamic frequencies'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=2400)
    parser.add_argument('--privileged-emc', action='store_true', help='read the protected EMC node with sudo -n cat')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            stream.write(json.dumps(snapshot(args.privileged_emc)) + '\n')
            stream.flush()
            time.sleep(1)


if __name__ == '__main__':
    main()
