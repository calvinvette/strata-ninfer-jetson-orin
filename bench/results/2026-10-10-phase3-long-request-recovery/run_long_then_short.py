"""Run a long real-model request followed by a short request on one server."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import requests


def request(base, model, text, max_tokens):
    body = {
        'model': model,
        'messages': [{'role': 'user', 'content': text}],
        'temperature': 0,
        'max_tokens': max_tokens,
        'chat_template_kwargs': {'enable_thinking': False},
    }
    start = time.monotonic()
    response = requests.post(base + '/v1/chat/completions', json=body, timeout=900)
    elapsed = time.monotonic() - start
    response.raise_for_status()
    data = response.json()
    return {
        'http_status': response.status_code,
        'elapsed_s': elapsed,
        'usage': data.get('usage'),
        'timings': data.get('timings'),
        'finish_reason': data.get('choices', [{}])[0].get('finish_reason'),
        'response_chars': len(data.get('choices', [{}])[0].get('message', {}).get('content', '')),
    }


def set_arg(values, name, value=None):
    if name in values:
        i = values.index(name)
        if value is not None:
            values[i + 1] = value
    elif value is None:
        values.append(name)
    else:
        values.extend([name, value])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18140)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    cfg['cwd'] = str(Path.cwd())
    cfg['args'] = [v for v in cfg['args'] if v != '--vision']
    for name, value in (('--expert-cache', 'auto'), ('--prefill', '512'), ('--max-context', '8192')):
        set_arg(cfg['args'], name, value)
    if '--no-prefill-borrow' not in cfg['args']:
        cfg['args'].append('--no-prefill-borrow')
    cfg.pop('vision', None)
    cfg['host'], cfg['port'] = '127.0.0.1', args.port
    cfg['log'] = str(out / 'engine.log')
    cfg['open_browser'] = False
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_INTEGRATION_TRACE': '1'}
    owned_cfg = out / 'server-config.json'
    owned_cfg.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f'http://127.0.0.1:{args.port}'
    result = {'port': args.port, 'status': 'not_run'}
    with (out / 'server.log').open('w') as log:
        server = subprocess.Popen(
            [sys.executable, '-m', 'serve.server', '--engine', 'strata', '--config',
             str(owned_cfg), '--host', '127.0.0.1', '--port', str(args.port)],
            cwd=cfg['cwd'], stdout=log, stderr=subprocess.STDOUT)
        result['server_pid'] = server.pid
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
            model = result['health']['model']
            clauses = [
                'This bounded service recovery probe describes a technical report about memory ownership, transfer scheduling, and request admission.',
                'The report distinguishes requested capacity from measured physical use, and records each allocation lifetime independently.',
                'A controller observes the complete request, preserves state at the accepted prefix, and releases temporary work after completion.',
                'The storage path compares mapped expert reads with asynchronous pread while retaining token and state checksums.',
            ]
            long_text = ' '.join(clauses[i % len(clauses)] for i in range(180))
            result['long'] = request(base, model, long_text, 256)
            result['short'] = request(base, model, 'Reply with the word ready.', 1)
            if result['short']['http_status'] != 200 or not result['short']['response_chars']:
                raise AssertionError('short recovery request returned no content')
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
