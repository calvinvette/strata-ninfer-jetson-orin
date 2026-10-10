"""Run real-model cancellation/recovery scenarios on an owned loopback server."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18125)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    cfg['args'] = list(cfg['args'])
    cfg['args'] = [v for v in cfg['args'] if v != '--vision']
    for flag, value in (('--expert-cache', 'auto'), ('--prefill', '512')):
        if flag in cfg['args']:
            cfg['args'][cfg['args'].index(flag) + 1] = value
        else:
            cfg['args'] += [flag, value]
    if '--no-prefill-borrow' not in cfg['args']:
        cfg['args'].append('--no-prefill-borrow')
    cfg.pop('vision', None)
    cfg['host'], cfg['port'] = '127.0.0.1', args.port
    cfg['log'] = str(out / 'engine.log')
    cfg['open_browser'] = False
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_INTEGRATION_TRACE': '1'}
    config_path = out / 'server-config.json'
    config_path.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f'http://127.0.0.1:{args.port}'
    with (out / 'server.log').open('w') as log:
        server = subprocess.Popen(
            [sys.executable, '-m', 'serve.server', '--engine', 'strata', '--config',
             str(config_path), '--host', '127.0.0.1', '--port', str(args.port)],
            cwd=cfg['cwd'], stdout=log, stderr=subprocess.STDOUT)
        result = {'server_pid': server.pid, 'port': args.port, 'status': 'not_run'}
        try:
            deadline = time.monotonic() + 360
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f'server exited before ready: {server.returncode}')
                try:
                    health = requests.get(base + '/health', timeout=5)
                    if health.ok and health.json().get('loaded'):
                        result['health'] = health.json()
                        break
                except requests.RequestException:
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError('server readiness timeout')
                time.sleep(0.5)
            completed = subprocess.run(
                [sys.executable, 'tools/integration/validate_protocol.py',
                 '--base-url', base, '--out', str(out / 'protocol.json')],
                cwd=cfg['cwd'], capture_output=True, text=True, timeout=900)
            result['protocol_returncode'] = completed.returncode
            result['protocol_stdout'] = completed.stdout
            result['protocol_stderr'] = completed.stderr
            result['protocol'] = json.loads((out / 'protocol.json').read_text())
            if completed.returncode:
                raise RuntimeError('one or more real-model protocol scenarios failed')
            result['status'] = 'pass'
            rc = 0
        except Exception as exc:
            result['status'] = 'fail'
            result['reason'] = f'{type(exc).__name__}: {exc}'
            rc = 1
        finally:
            result['server_returncode_before_stop'] = server.poll()
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
            result['server_returncode_after_stop'] = server.poll()
            (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
        return rc


if __name__ == '__main__':
    raise SystemExit(main())
