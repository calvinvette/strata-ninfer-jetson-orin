#!/usr/bin/env python3
"""One-pass local API driver without benchmark_control.py's automatic warmup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request


def call(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3600) as response:
        return json.load(response)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--workloads', type=Path, required=True)
    ap.add_argument('--cells', nargs='+', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    cfg['log'] = str((args.output.parent / 'engine.log').resolve())
    owned_config = args.output.parent / 'server-config.json'
    owned_config.write_text(json.dumps(cfg, indent=2) + '\n')
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in cfg.get('env', {}).items()})
    base = f"http://127.0.0.1:{cfg['port']}"
    server = subprocess.Popen([sys.executable, '-m', 'serve.server', '--engine', 'strata',
                               '--config', str(owned_config.resolve()), '--host', '127.0.0.1',
                               '--port', str(cfg['port'])], cwd=cfg['cwd'], env=env)
    try:
        deadline = time.monotonic() + 240
        while True:
            if server.poll() is not None:
                raise RuntimeError(f'server exited before readiness: {server.returncode}')
            try:
                health = call(base + '/health')
                if health.get('model'):
                    break
            except (urllib.error.URLError, OSError):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError('server readiness deadline')
            time.sleep(0.5)
        cells = {c['cell']: c for c in json.loads(args.workloads.read_text())['workloads']}
        output = {'health': health, 'checks': []}
        for name in args.cells:
            cell = cells[name]
            body = {'model': health['model'], 'messages': cell['messages'],
                    'chat_template_kwargs': cell['chat_template_kwargs'],
                    'temperature': 0, 'max_tokens': cell['generate_tokens']}
            started = time.monotonic()
            response = call(base + '/v1/chat/completions', body)
            elapsed = time.monotonic() - started
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            output['checks'].append({'cell': name, 'elapsed_s': elapsed,
                                     'content_sha256': hashlib.sha256(content.encode()).hexdigest(),
                                     'content': content, 'response': response})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(output, indent=2) + '\n')
            print(name, len(content), output['checks'][-1]['content_sha256'], flush=True)
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == '__main__':
    raise SystemExit(main())
