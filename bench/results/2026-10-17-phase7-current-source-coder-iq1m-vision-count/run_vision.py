"""Run one bounded local image request against an owned candidate server."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request


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
    p.add_argument('--expert-cache', type=int,
                   help='override the profile cache argument; default keeps the supplied config')
    p.add_argument('--vision-max-tokens', type=int, default=16)
    p.add_argument('--vision-min-tokens', type=int, default=16)
    a = p.parse_args()
    if a.vision_min_tokens < 1 or a.vision_max_tokens < a.vision_min_tokens:
        p.error('vision token limits must satisfy 1 <= min <= max')
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
    if a.expert_cache is not None:
        set_arg(args, '--expert-cache', str(a.expert_cache))
    set_arg(args, '--max-context', '8192')
    set_arg(args, '--vision')
    cfg['args'] = args
    cfg['vision'] = {
        'exe': str(a.vision_exe.resolve()), 'mmproj': str(a.mmproj.resolve()),
        'model': str(model_path),
        'gpu': True, 'threads': 8, 'min_tokens': a.vision_min_tokens,
        'max_tokens': a.vision_max_tokens,
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
        result = {'server_pid': server.pid, 'port': a.port,
                  'vision_min_tokens': a.vision_min_tokens,
                  'vision_max_tokens': a.vision_max_tokens, 'status': 'not_run'}
        try:
            deadline = time.monotonic() + 360
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f'server exited before ready: {server.returncode}')
                try:
                    with urllib.request.urlopen(base + '/health', timeout=5) as response:
                        health = json.load(response)
                    if health.get('loaded'):
                        result['health'] = health
                        break
                except (urllib.error.URLError, OSError, ValueError):
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError('server readiness timeout')
                time.sleep(0.5)
            data = base64.b64encode(a.fixture.read_bytes()).decode('ascii')
            body = {
                'model': result['health']['model'],
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text', 'text': 'Count the black circles in each colored quadrant. Return one line exactly in this format: TL=<count> TR=<count> BL=<count> BR=<count> SUM=<total>. Use the positions of the quadrants as viewed in the image.'},
                    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + data}},
                ]}],
                'temperature': 0, 'max_tokens': 32,
                'chat_template_kwargs': {'enable_thinking': False},
            }
            start = time.monotonic()
            request = urllib.request.Request(base + '/v1/chat/completions',
                                             data=json.dumps(body).encode(),
                                             headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=600) as response:
                result['response_status'] = response.status
                result['response'] = json.load(response)
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
