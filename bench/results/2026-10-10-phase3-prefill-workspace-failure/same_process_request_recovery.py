"""Refuse a post-warmup CUDA allocation and require service restart recovery."""
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
    ap.add_argument('--shim', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--port', type=int, default=18126)
    args = ap.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    marker = out / 'inject.now'
    cfg = json.loads(args.config.read_text())
    cfg['args'] = list(cfg['args'])
    for flag, value in (('--expert-cache', 'auto'), ('--prefill', '512')):
        if flag in cfg['args']:
            cfg['args'][cfg['args'].index(flag) + 1] = value
        else:
            cfg['args'] += [flag, value]
    if '--no-prefill-borrow' not in cfg['args']:
        cfg['args'].append('--no-prefill-borrow')
    cfg['host'], cfg['port'] = '127.0.0.1', args.port
    cfg['log'] = str(out / 'engine.log')
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_INTEGRATION_TRACE': '1',
                  'STRATA_FAIL_ALLOC_MARKER': str(marker),
                  'STRATA_FAIL_ALLOC_MIN_BYTES': str(1 << 20),
                  'LD_PRELOAD': str(args.shim.resolve())}
    config_path = out / 'server-config.json'
    config_path.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f'http://127.0.0.1:{args.port}'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', args.port))
    with (out / 'server.log').open('w') as log:
        server = subprocess.Popen(
            [sys.executable, '-m', 'serve.server', '--engine', 'strata', '--config',
             str(config_path), '--host', '127.0.0.1', '--port', str(args.port)],
            cwd=cfg['cwd'], stdout=log, stderr=subprocess.STDOUT)
        result = {'checks': [], 'server_pid': server.pid, 'port': args.port,
                  'scope': 'same Python service; engine process is expected to restart after abort',
                  'injection': 'one cudaMalloc >=1MiB after readiness marker'}
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

            # A 511-token prompt exercises prefill-owned scratch after model warmup.
            body = {'model': result['health']['model'],
                    'messages': [{'role': 'user', 'content': 'Remember this context: ' +
                                  'red green blue yellow orange purple ' * 256}],
                    'temperature': 0, 'max_tokens': 1,
                    'chat_template_kwargs': {'enable_thinking': False}}
            marker.write_text('inject on next qualifying cudaMalloc\n')
            first = requests.post(base + '/v1/chat/completions', json=body, timeout=300)
            first_text = first.text[:4000]
            engine_log = (out / 'engine.log').read_text(errors='replace')
            hit = 'TEST_SHIM: refused one post-marker cudaMalloc' in engine_log
            result['checks'].append({'name': 'post_warmup_injected_request',
                                     'http_status': first.status_code,
                                     'body_excerpt': first_text,
                                     'injection_observed': hit})
            if not hit:
                raise AssertionError('no qualifying request-path cudaMalloc was refused')
            if first.status_code < 400:
                raise AssertionError(f'injected request unexpectedly succeeded: HTTP {first.status_code}')

            marker.unlink()
            recovery_body = {'model': result['health']['model'],
                             'messages': [{'role': 'user', 'content': 'Reply with exactly: recovered'}],
                             'temperature': 0, 'max_tokens': 1,
                             'chat_template_kwargs': {'enable_thinking': False}}
            second = requests.post(base + '/v1/chat/completions', json=recovery_body, timeout=240)
            second_obj = second.json()
            result['checks'].append({'name': 'service_recovery_after_engine_restart', 'http_status': second.status_code,
                                     'body': second_obj})
            second.raise_for_status()
            if second_obj.get('usage', {}).get('completion_tokens', 0) != 1:
                raise AssertionError(f'expected one recovery token, got {second_obj.get("usage")}')
            if server.poll() is not None:
                raise AssertionError(f'server exited after recovery: {server.returncode}')
            service_log = (out / 'server.log').read_text(errors='replace')
            result['engine_restart_observed'] = service_log.count('starting it again')
            if result['engine_restart_observed'] != 1 or 'the engine is running again' not in service_log:
                raise AssertionError('service log did not show exactly one engine restart before recovery')
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
