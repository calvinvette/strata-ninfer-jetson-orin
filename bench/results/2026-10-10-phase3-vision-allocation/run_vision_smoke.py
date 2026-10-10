"""Run one bounded local image request against an owned candidate server."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys
import time
import requests


def set_arg(args, flag, value=None):
    if flag in args:
        i = args.index(flag)
        if value is None:
            return
        args[i + 1] = value
    elif value is None:
        args.append(flag)
    else:
        args.extend([flag, value])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--vision-exe', type=Path, required=True)
    p.add_argument('--mmproj', type=Path, required=True)
    p.add_argument('--port', type=int, default=18124)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(a.config.read_text())
    cfg['cwd'] = str(Path.cwd())
    cfg['host'], cfg['port'] = '127.0.0.1', a.port
    cfg['log'] = str((out / 'engine.log').resolve())
    cfg['open_browser'] = False
    args = list(cfg['args'])
    try:
        model_path = Path(args[args.index('--native') + 1]).resolve()
    except (ValueError, IndexError):
        raise SystemExit('server config must provide --native <model>')
    set_arg(args, '--expert-cache', '5000')
    set_arg(args, '--max-context', '8192')
    set_arg(args, '--vision')
    cfg['args'] = args
    cfg['vision'] = {
        'exe': str(a.vision_exe.resolve()), 'mmproj': str(a.mmproj.resolve()),
        'model': str(model_path),
        'gpu': True, 'threads': 8, 'min_tokens': 16, 'max_tokens': 16,
    }
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_INTEGRATION_TRACE': '1'}
    owned_cfg = out / 'server-config.json'
    owned_cfg.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f'http://127.0.0.1:{a.port}'
    with (out / 'server.log').open('w') as log:
        server = subprocess.Popen(
            [sys.executable, '-m', 'serve.server', '--engine', 'strata', '--config',
             str(owned_cfg), '--host', '127.0.0.1', '--port', str(a.port)],
            cwd=cfg['cwd'], stdout=log, stderr=subprocess.STDOUT)
        result = {'server_pid': server.pid, 'port': a.port, 'status': 'not_run'}
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
            data = base64.b64encode(a.fixture.read_bytes()).decode('ascii')
            body = {
                'model': result['health']['model'],
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text', 'text': 'Briefly describe the colors and patterns in this image.'},
                    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + data}},
                ]}],
                'temperature': 0, 'max_tokens': 48,
                'chat_template_kwargs': {'enable_thinking': False},
            }
            start = time.monotonic()
            response = requests.post(base + '/v1/chat/completions', json=body, timeout=600)
            result['response_status'] = response.status_code
            response.raise_for_status()
            result['response'] = response.json()
            result['request_elapsed_s'] = time.monotonic() - start
            result['fixture_sha256'] = __import__('hashlib').sha256(a.fixture.read_bytes()).hexdigest()
            if not result['response'].get('choices', [{}])[0].get('message', {}).get('content', '').strip():
                raise AssertionError('image request returned empty assistant content')
            result['status'] = 'pass'
            return_code = 0
        except Exception as exc:
            result['status'] = 'fail'
            result['reason'] = f'{type(exc).__name__}: {exc}'
            return_code = 1
        finally:
            result['server_pid_before_stop'] = server.poll()
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
        return return_code


if __name__ == '__main__':
    raise SystemExit(main())
