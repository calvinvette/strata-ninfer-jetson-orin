"""Inject a one-shot prefill allocation failure, then verify same-server recovery."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--port', type=int, default=18123)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    cfg['args'] = list(cfg['args'])
    for flag, value in (('--expert-cache', 'auto'), ('--prefill', '512')):
        if flag in cfg['args']:
            cfg['args'][cfg['args'].index(flag) + 1] = value
        else:
            cfg['args'] += [flag, value]
    if '--no-prefill-borrow' not in cfg['args']:
        cfg['args'].append('--no-prefill-borrow')
    cfg['port'] = args.port
    cfg['host'] = '127.0.0.1'
    cfg['log'] = str((args.output_dir / 'engine.log').resolve())
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_INTEGRATION_TRACE': '1'}
    owned_cfg = args.output_dir / 'server-config.json'
    owned_cfg.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f'http://127.0.0.1:{args.port}'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', args.port))
    with (args.output_dir / 'server.log').open('w') as server_log:
        server = subprocess.Popen(
            [sys.executable, '-m', 'serve.server', '--engine', 'strata', '--config',
             str(owned_cfg.resolve()), '--host', '127.0.0.1', '--port', str(args.port)],
            cwd=cfg['cwd'], stdout=server_log, stderr=subprocess.STDOUT)
        result = {'checks': [], 'server_pid': server.pid, 'port': args.port}
        try:
            deadline = time.monotonic() + 240
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f'server exited before readiness: {server.returncode}')
                try:
                    health = requests.get(base + '/health', timeout=3)
                    if health.ok and health.json().get('model'):
                        result['health'] = health.json()
                        break
                except requests.RequestException:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError('server readiness deadline')
                time.sleep(0.5)

            body = {'model': result['health']['model'],
                    'messages': [{'role': 'user', 'content': 'Reply with exactly: recovered'}],
                    'temperature': 0, 'max_tokens': 1,
                    'chat_template_kwargs': {'enable_thinking': False}}
            first = requests.post(base + '/v1/chat/completions', json=body, timeout=240)
            result['checks'].append({'name': 'injected_failure', 'http_status': first.status_code,
                                     'body': first.json() if 'application/json' in first.headers.get('content-type', '')
                                     else first.text[:1000]})
            first_body = result['checks'][-1]['body']
            first_text = json.dumps(first_body, ensure_ascii=False)
            if first.status_code == 200 or 'GEMM scratch does not fit' not in first_text:
                raise AssertionError('first request did not surface the injected prefill GEMM workspace failure')

            second = requests.post(base + '/v1/chat/completions', json=body, timeout=240)
            second_body = second.json()
            result['checks'].append({'name': 'same_process_recovery', 'http_status': second.status_code,
                                     'body': second_body})
            second.raise_for_status()
            if second_body.get('usage', {}).get('completion_tokens', 0) != 1:
                raise AssertionError(f'expected one completion token, got {second_body.get("usage")}')
            result['server_pid_after_recovery'] = server.poll()
            if server.poll() is not None:
                raise AssertionError(f'server exited after recovery request: {server.returncode}')
            result['engine_starts'] = sum(1 for line in (args.output_dir / 'server.log').read_text().splitlines()
                                          if 'engine started:' in line)
            if result['engine_starts'] != 1:
                raise AssertionError(f'expected same engine instance, observed {result["engine_starts"]} starts')
            result['status'] = 'pass'
            print(json.dumps(result, indent=2), flush=True)
            return 0
        except Exception as exc:
            result['status'] = 'fail'
            result['reason'] = f'{type(exc).__name__}: {exc}'
            print(json.dumps(result, indent=2), flush=True)
            return 1
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


if __name__ == '__main__':
    raise SystemExit(main())
