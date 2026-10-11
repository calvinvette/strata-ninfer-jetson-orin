"""Cancel a real-model long prefill, then verify same-process API recovery."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

from run_control import write_result


def post_json(url, body, timeout=120):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--long-workload', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cancel-after-s', type=float, default=1.0)
    args = parser.parse_args()
    if args.output.exists() or args.cancel_after_s <= 0:
        parser.error('output must be new and cancel delay must be positive')
    cfg = json.loads(args.config.read_text())
    if int(cfg['port']) < 1 or cfg.get('host', '127.0.0.1') != '127.0.0.1':
        parser.error('use an explicit loopback server configuration')
    workloads = json.loads(args.long_workload.read_text())['workloads']
    if len(workloads) != 1 or workloads[0]['prompt_tokens'] < 1024:
        parser.error('provide exactly one workload with at least 1,024 formatted prompt tokens')
    workload = workloads[0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{cfg['port']}"
    cfg['log'] = str((args.output.parent / 'engine.log').resolve())
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_TRACE': '1'}
    owned_config = args.output.parent / 'server-config.json'
    owned_config.write_text(json.dumps(cfg, indent=2) + '\n')
    result = {
        'scope': 'single long-prefill stream cancellation followed by same-process short API recovery',
        'model': cfg.get('model_name'), 'long_cell': workload['cell'],
        'requested_prompt_tokens': workload['prompt_tokens'],
        'cancel_after_s': args.cancel_after_s, 'checks': [],
    }
    write_result(args.output, result)
    server = subprocess.Popen(
        [sys.executable, '-m', 'serve.server', '--engine', 'strata',
         '--config', str(owned_config.resolve()), '--host', '127.0.0.1',
         '--port', str(cfg['port'])], cwd=cfg['cwd'])
    try:
        deadline = time.monotonic() + 300
        health = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f'server exited before readiness: {server.returncode}')
            try:
                with urllib.request.urlopen(base + '/health', timeout=5) as response:
                    health = json.load(response)
                if health.get('model'):
                    break
            except (urllib.error.URLError, OSError, ValueError):
                time.sleep(0.5)
        if not health or not health.get('model'):
            raise TimeoutError('server readiness deadline')
        result['health'] = health
        body = {
            'model': health['model'], 'messages': workload['messages'],
            'chat_template_kwargs': workload['chat_template_kwargs'],
            'temperature': 0, 'max_tokens': max(64, workload['generate_tokens']),
            'stream': True,
        }
        row = {'check': 'cancel_long_prefill', 'status': 'started'}
        result['checks'].append(row)
        write_result(args.output, result)
        request = urllib.request.Request(
            base + '/v1/chat/completions', data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'})
        start = time.monotonic()
        with urllib.request.urlopen(request, timeout=600) as response:
            row['http_status'] = response.status
            row['response_headers_at_s'] = time.monotonic() - start
            time.sleep(args.cancel_after_s)
        row.update(status='pass', reason='client stream closed after bounded delay',
                   elapsed_s=time.monotonic() - start)
        write_result(args.output, result)

        recovery = {'check': 'short_request_recovery', 'status': 'started'}
        result['checks'].append(recovery)
        write_result(args.output, result)
        short_body = {
            'model': health['model'],
            'messages': [{'role': 'user', 'content': 'Reply with exactly: Hello Orin!'}],
            'temperature': 0, 'max_tokens': 24,
            'chat_template_kwargs': {'enable_thinking': False},
        }
        short_start = time.monotonic()
        response = post_json(base + '/v1/chat/completions', short_body)
        recovery['elapsed_s'] = time.monotonic() - short_start
        recovery['response'] = response
        content = response['choices'][0]['message'].get('content', '').strip()
        recovery.update(status='pass' if content == 'Hello Orin!' else 'fail',
                        reason='expected recovery response' if content == 'Hello Orin!' else
                        f'unexpected recovery content: {content!r}')
        metrics_req = urllib.request.Request(base + '/metrics')
        with urllib.request.urlopen(metrics_req, timeout=10) as metrics_response:
            result['metrics_after_recovery'] = json.load(metrics_response)
        result['server_alive_after_recovery'] = server.poll() is None
        if not result['server_alive_after_recovery']:
            recovery.update(status='fail', reason=f'server exited: {server.returncode}')
        write_result(args.output, result)
        return int(recovery['status'] != 'pass')
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        if result['checks'] and result['checks'][-1].get('status') == 'started':
            result['checks'][-1].update(status='fail', reason=result['error'])
        write_result(args.output, result)
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
