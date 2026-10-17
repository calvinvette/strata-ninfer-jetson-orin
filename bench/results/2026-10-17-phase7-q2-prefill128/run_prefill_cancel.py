#!/usr/bin/env python3
"""Disconnect during observed long-prompt prefill, then test same-service recovery."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18884)
    parser.add_argument('--progress-timeout', type=int, default=240)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    workload = json.loads(args.workload.read_text())['workloads'][0]
    cfg['port'] = args.port
    cfg['host'] = '127.0.0.1'
    cfg['log'] = str((args.output / 'engine.log').resolve())
    cfg['env'] = dict(cfg.get('env', {}))
    cfg['env']['STRATA_INTEGRATION_TRACE'] = '1'
    config_path = args.output / 'server-config.json'
    config_path.write_text(json.dumps(cfg, indent=2) + '\n')
    server_stdout_path = args.output / 'server.stdout.log'
    base = f"http://127.0.0.1:{args.port}"
    result = {'status': 'not_run', 'configured_context': next(
        int(cfg['args'][i + 1]) for i, value in enumerate(cfg['args'])
        if value == '--max-context'), 'expected_prompt_tokens': workload['prompt_tokens'],
        'cancel': {}, 'recovery': {}}
    with server_stdout_path.open('w', encoding='utf-8') as server_stdout:
        server = subprocess.Popen(
            [sys.executable, '-m', 'serve.server', '--engine', 'strata', '--config',
             str(config_path.resolve()), '--host', '127.0.0.1', '--port', str(args.port)],
            cwd=cfg['cwd'], env=os.environ | cfg['env'], stdout=server_stdout,
            stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 360
        while True:
            if server.poll() is not None:
                raise RuntimeError(f'server exited before ready: {server.returncode}')
            try:
                health = requests.get(base + '/health', timeout=5).json()
                if health.get('loaded'):
                    result['health'] = health
                    break
            except requests.RequestException:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('service readiness deadline')
            time.sleep(0.5)

        engine_log = Path(cfg['log'])
        body = {'model': health['model'], 'messages': workload['messages'],
                'temperature': 0, 'max_tokens': workload['generate_tokens'],
                'chat_template_kwargs': {'enable_thinking': False}}
        prefill_started = time.monotonic()
        request_body = json.dumps(dict(body, stream=True), separators=(',', ':')).encode()
        request_socket = socket.create_connection(('127.0.0.1', args.port), timeout=15)
        headers = (f'POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:{args.port}\r\n'
                   'Content-Type: application/json\r\nAccept: text/event-stream\r\n'
                   f'Content-Length: {len(request_body)}\r\nConnection: keep-alive\r\n\r\n').encode()
        request_socket.sendall(headers + request_body)
        deadline = time.monotonic() + args.progress_timeout
        progress = None
        progress_line = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                request_socket.close()
                raise RuntimeError(f'server exited during prefill: {server.returncode}')
            for log_path in (engine_log, server_stdout_path):
                log_text = log_path.read_text(errors='replace') if log_path.exists() else ''
                for line in log_text.splitlines():
                    match = re.search(r'reading the prompt: ([0-9,]+) of ([0-9,]+) tokens', line)
                    if match:
                        seen, total = (int(value.replace(',', '')) for value in match.groups())
                        if total == workload['prompt_tokens'] and 0 < seen < total:
                            progress, progress_line = seen, line
                            break
                if progress is not None:
                    break
            if progress is not None:
                break
            time.sleep(0.1)
        if progress is None:
            request_socket.close()
            raise TimeoutError('no incomplete engine prompt-progress record before deadline')
        request_socket.shutdown(socket.SHUT_RDWR)
        request_socket.close()
        close_time = time.monotonic()

        cancel_deadline = time.monotonic() + 60
        cancel_line = None
        while time.monotonic() < cancel_deadline:
            logs = [path.read_text(errors='replace') for path in
                    (engine_log, server_stdout_path) if path.exists()]
            candidates = [line for text in logs for line in text.splitlines()
                          if 'done:' in line and 'cancel=True' in line]
            if candidates:
                cancel_line = candidates[-1]
                break
            if server.poll() is not None:
                raise RuntimeError(f'server exited after prefill disconnect: {server.returncode}')
            time.sleep(0.1)
        if cancel_line is None:
            raise TimeoutError('engine did not log cancellation after observed prefill progress')
        result['cancel'] = {
            'status': 'pass', 'prompt_tokens': workload['prompt_tokens'],
            'engine_progress_tokens_before_disconnect': progress,
            'engine_progress_record': progress_line,
            'disconnect_delay_s': close_time - prefill_started,
            'cancel_record': cancel_line,
        }

        recovery_body = {'model': health['model'],
                         'messages': [{'role': 'user', 'content': 'Reply with exactly Hello Orin!'}],
                         'temperature': 0, 'max_tokens': 24,
                         'chat_template_kwargs': {'enable_thinking': False}}
        recovery = requests.post(base + '/v1/chat/completions', json=recovery_body,
                                 timeout=120)
        recovery.raise_for_status()
        recovery_json = recovery.json()
        answer = recovery_json['choices'][0]['message']['content'].strip()
        result['recovery'] = {'status': 'pass' if answer == 'Hello Orin!' else 'fail',
                              'answer': answer,
                              'prompt_tokens': recovery_json.get('usage', {}).get('prompt_tokens'),
                              'completion_tokens': recovery_json.get('usage', {}).get('completion_tokens')}
        if result['recovery']['status'] != 'pass':
            raise RuntimeError(f"same-service recovery answer mismatch: {answer!r}")
        result['status'] = 'pass'
        result['reason'] = 'disconnect followed observed prompt progress; engine cancelled and same-service recovery passed'
        return 0
    except Exception as exc:
        result['status'] = 'fail'
        result['reason'] = f'{type(exc).__name__}: {exc}'
        return 1
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
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
