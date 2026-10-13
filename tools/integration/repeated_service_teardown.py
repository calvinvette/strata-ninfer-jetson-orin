"""Exercise fresh Strata service startup, one request, teardown and reload."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from api_control_block import check_port
from run_control import write_result


def cycle_config(source, port, output):
    cfg = json.loads(json.dumps(source))
    cfg['port'] = port
    cfg['log'] = str((output / 'engine.log').resolve())
    return cfg


def strata_engine_pids():
    found = set()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            argv = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except OSError:
            continue
        if '--serve' in argv and any(Path(arg).name == 'strata' for arg in argv):
            found.add(int(entry.name))
    return found


def wait_for_teardown(port, baseline, timeout=20):
    deadline = time.monotonic() + timeout
    while True:
        listener_closed = True
        try:
            check_port(port)
        except OSError:
            listener_closed = False
        remaining = strata_engine_pids() - baseline
        if listener_closed and not remaining:
            return True, sorted(remaining)
        if time.monotonic() >= deadline:
            return listener_closed, sorted(remaining)
        time.sleep(.25)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--warmup-workloads', type=Path, required=True,
                        help='distinct-length prompt used for the one warmup request')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cycles', type=int, default=3)
    parser.add_argument('--first-port', type=int, default=18840)
    parser.add_argument('--python', default=sys.executable)
    args = parser.parse_args()
    if args.cycles < 2 or args.cycles > 10 or args.first_port < 1024:
        parser.error('cycles must be between 2 and 10 and first port must be unprivileged')
    if args.output.exists():
        parser.error('new output directory required')
    source = json.loads(args.config.read_text())
    workloads = json.loads(args.workloads.read_text())
    if len(workloads.get('workloads', [])) != 1:
        parser.error('exactly one prepared workload required')
    output = args.output.resolve()
    output.mkdir(parents=True)
    baseline = strata_engine_pids()
    if baseline:
        parser.error(f'refusing to run while Strata engine processes are already active: {sorted(baseline)}')
    campaign = {'planned_cycles': args.cycles, 'status': 'not_run', 'cycles': [],
                'scope': 'fresh loopback service per cycle; one distinct warmup and one measured request; teardown checked before next cycle'}
    manifest = output / 'campaign.json'
    write_result(manifest, campaign)
    api = Path(__file__).with_name('api_control_block.py')
    for index in range(args.cycles):
        number = index + 1
        name = f'cycle-{number:02d}'
        directory = output / name
        directory.mkdir()
        port = args.first_port + index
        cfg = cycle_config(source, port, directory)
        cfgpath = directory / 'config.json'
        cfgpath.write_text(json.dumps(cfg, indent=2) + '\n')
        row = {'cycle': number, 'port': port, 'status': 'not_run', 'reason': 'request not started'}
        campaign['cycles'].append(row)
        write_result(manifest, campaign)
        command = [args.python, str(api), '--config', str(cfgpath.resolve()),
                   '--workloads', str(args.workloads.resolve()),
                   '--warmup-workloads', str(args.warmup_workloads.resolve()),
                   '--output', str((directory / 'requests.json').resolve()),
                   '--variant', 'candidate', '--rounds', '1', '--no-trace']
        with (directory / 'runner.txt').open('w') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        request_path = directory / 'requests.json'
        if request_path.exists():
            result = json.loads(request_path.read_text())
            measured = [x for x in result.get('checks', []) if not x.get('warmup')]
            row['measured_samples'] = len(measured)
            row['request_statuses'] = [x.get('status') for x in measured]
            row['prompt_tokens'] = [x.get('response', {}).get('usage', {}).get('prompt_tokens') for x in measured]
            row['completion_tokens'] = [x.get('response', {}).get('usage', {}).get('completion_tokens') for x in measured]
        row['runner_returncode'] = code
        row['listener_closed'], remaining = wait_for_teardown(port, baseline)
        row['remaining_strata_engine_pids'] = remaining
        row['processes_closed'] = not remaining
        if (code == 0 and row.get('measured_samples') == 1
                and row.get('request_statuses') == ['pass']
                and row['listener_closed'] and row['processes_closed']):
            row.update(status='pass', reason='request passed; listener and engine process released')
        else:
            row.setdefault('reason', 'request, listener, process or supervisor check failed')
            row['status'] = 'fail'
        write_result(manifest, campaign)
        print(name, row['status'], row['reason'], flush=True)
        if row['status'] != 'pass':
            for pending in range(index + 1, args.cycles):
                campaign['cycles'].append({'cycle': pending + 1, 'status': 'not_run',
                                           'reason': 'not launched after failed teardown/request check'})
            write_result(manifest, campaign)
            return 1
    campaign['status'] = 'pass'
    write_result(manifest, campaign)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
