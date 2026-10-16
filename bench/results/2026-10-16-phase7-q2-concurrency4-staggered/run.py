#!/usr/bin/env python3
"""Measure four-slot occupancy with descending prompt lengths and sampled API metrics."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tools' / 'integration'))
from benchmark_control import request, stream_request  # noqa: E402


def main():
    out = Path(sys.argv[1])
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    here = Path(__file__).resolve().parent
    cfg = json.loads((here / 'config.json').read_text())
    workloads = json.loads((here / 'workloads.json').read_text())['workloads']
    warmup = json.loads((here / 'warmup.json').read_text())['workloads'][0]
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', int(cfg['port'])))
    cfg['log'] = str((out / 'engine.log').resolve())
    owned = out / 'server-config.json'
    owned.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f"http://127.0.0.1:{cfg['port']}"
    result = {
        'status': 'not_run',
        'binary_sha256': hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),
        'config_sha256': hashlib.sha256((here / 'config.json').read_bytes()).hexdigest(),
        'workload_sha256': hashlib.sha256((here / 'workloads.json').read_bytes()).hexdigest(),
        'requests': [], 'max_running': 0, 'max_active_metric_slots': 0,
        'max_active_http_slots': 0, 'samples': 0,
    }
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    server = subprocess.Popen([sys.executable, '-m', 'serve.server', '--engine', 'strata',
                               '--config', str(owned.resolve()), '--host', '127.0.0.1',
                               '--port', str(cfg['port'])], cwd=cfg['cwd'],
                              env=os.environ | cfg.get('env', {}))
    try:
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f'server exited during startup: {server.returncode}')
            try:
                health = request(base, '/health', timeout=5)
                if health.get('model'):
                    break
            except (urllib.error.URLError, OSError, ValueError):
                time.sleep(0.5)
        else:
            raise TimeoutError('server readiness deadline')
        result['health'] = health
        warm_body = {'model': health['model'], 'messages': warmup['messages'],
                     'chat_template_kwargs': warmup.get('chat_template_kwargs', {}),
                     'temperature': 0, 'max_tokens': warmup['generate_tokens']}
        result['warmup'] = stream_request(base, warm_body)[0]

        started = {}
        release = [threading.Event() for _ in workloads]

        def send(index, workload):
            release[index].wait()
            started[index] = time.monotonic()
            body = {'model': health['model'], 'messages': workload['messages'],
                    'chat_template_kwargs': workload['chat_template_kwargs'],
                    'temperature': 0, 'max_tokens': workload['generate_tokens']}
            response, observed = stream_request(base, body)
            usage = response.get('usage', {})
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            marker = workload['expected_code']
            return {
                'cell': workload['cell'], 'expected_prompt_tokens': workload['prompt_tokens'],
                'prompt_tokens': usage.get('prompt_tokens'),
                'completion_tokens': usage.get('completion_tokens', 0),
                'expected_code': marker, 'marker_count': content.count(marker),
                'quality_pass': usage.get('prompt_tokens') == workload['prompt_tokens']
                                and usage.get('completion_tokens', 0) > 0
                                and content.count(marker) == 1,
                'content': content, 'client_start_monotonic_s': started[index],
                'ttft_s': observed.get('first_visible_delta_s'),
            }

        metrics_path = out / 'metrics.jsonl'
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(send, i, w) for i, w in enumerate(workloads)]
            for i, gate in enumerate(release):
                gate.set()
                if i + 1 < len(release):
                    time.sleep(0.5)
            while not all(f.done() for f in futures):
                sample = {'monotonic_s': time.monotonic()}
                try:
                    metrics = request(base, '/metrics', timeout=5).get('live', {})
                    sample['running'] = metrics.get('running', 0)
                    sample['waiting'] = metrics.get('waiting', 0)
                    sample['outside_slots'] = metrics.get('outside_slots', 0)
                    slots = metrics.get('slots', [])
                    sample['active_metric_slots'] = sum(s.get('state') != 'idle' for s in slots)
                    result['max_running'] = max(result['max_running'], int(sample['running']))
                    result['max_active_metric_slots'] = max(result['max_active_metric_slots'],
                                                            sample['active_metric_slots'])
                except (urllib.error.URLError, OSError, ValueError) as exc:
                    sample['metrics_error'] = f'{type(exc).__name__}: {exc}'
                try:
                    slots_http = request(base, '/slots', timeout=5)
                    sample['active_http_slots'] = sum(bool(s.get('is_processing')) for s in slots_http)
                    result['max_active_http_slots'] = max(result['max_active_http_slots'],
                                                          sample['active_http_slots'])
                except (urllib.error.URLError, OSError, ValueError) as exc:
                    sample['slots_error'] = f'{type(exc).__name__}: {exc}'
                with metrics_path.open('a') as stream:
                    stream.write(json.dumps(sample) + '\n')
                result['samples'] += 1
                time.sleep(0.05)
            result['requests'] = [f.result() for f in futures]
        result['batch_slots_reported'] = request(base, '/v1/status', timeout=10).get('concurrency', {}).get('serving')
        result['quality_pass'] = len(result['requests']) == 4 and all(x['quality_pass'] for x in result['requests'])
        result['all_slots_admitted'] = result['batch_slots_reported'] == 4
        result['four_way_overlap_observed'] = max(result['max_active_metric_slots'],
                                                    result['max_active_http_slots']) >= 4
        result['status'] = 'pass' if all(result[k] for k in ('quality_pass', 'all_slots_admitted',
                                                              'four_way_overlap_observed')) else 'fail'
        result['reason'] = ('four distinct staggered requests overlapped in four slots and passed exact-marker checks'
                            if result['status'] == 'pass' else
                            'quality, four-slot admission, or four-way overlap gate failed')
        return 0 if result['status'] == 'pass' else 1
    except Exception as exc:
        result['status'] = 'fail'
        result['reason'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == '__main__':
    raise SystemExit(main())
