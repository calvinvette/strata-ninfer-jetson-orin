"""Cancel a real-model long prefill, then verify same-process API recovery."""
import argparse
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from run_control import write_result


STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full',
              'kv', 'mtp', 'stale', 'ple_prev')


def final_state(log_path):
    found = []
    for line in Path(log_path).read_text(encoding='utf-8').splitlines():
        if line.startswith('strata serve: STATE_HASH L='):
            fields = dict(re.findall(r'([A-Za-z_]+)=([0-9a-fA-F,-]+)', line))
            if set(STATE_KEYS).issubset(fields):
                found.append({key: fields[key] for key in STATE_KEYS})
    if not found:
        raise RuntimeError(f'no complete persistent-state fingerprint in {log_path}')
    return found[-1]


def require_free_loopback_port(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))


def canceled_prefill_line(log_path):
    for line in reversed(Path(log_path).read_text(encoding='utf-8').splitlines()):
        if line.startswith('strata serve: prompt ') and line.endswith('(cancelled)'):
            generated = re.search(r',\s*(\d+) generated in ', line)
            read = re.search(r'\+\s*(\d+) of (\d+) read in ', line)
            if generated and read:
                return {'line': line, 'generated_tokens': int(generated.group(1)),
                        'read_tokens': int(read.group(1)), 'prompt_tokens': int(read.group(2))}
    return None


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
    parser.add_argument('--compare-recovery-state', action='store_true',
                        help='compare recovered short request state with a fresh-service reference')
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
    if args.compare_recovery_state:
        cfg['env'].update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1'})
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
        cancel_deadline = time.monotonic() + 120
        cancel_record = None
        while time.monotonic() < cancel_deadline:
            cancel_record = canceled_prefill_line(cfg['log'])
            if cancel_record:
                break
            if server.poll() is not None:
                break
            time.sleep(0.25)
        cancel_ok = cancel_record is not None and cancel_record['generated_tokens'] == 0
        row.update(status='pass' if cancel_ok else 'fail',
                   reason='engine logged canceled prefill with zero generated tokens' if cancel_ok else
                   'engine cancellation summary was absent or generated tokens after client close',
                   elapsed_s=time.monotonic() - start, engine_cancellation=cancel_record)
        write_result(args.output, result)
        if not cancel_ok:
            return 1

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
        if args.compare_recovery_state:
            recovery_state = final_state(cfg['log'])
            # Release the full runtime before loading the reference model; Orin
            # has one physical RAM authority and cannot budget two copies here.
            server.terminate()
            server.wait(timeout=30)
            ref_cfg = dict(cfg)
            ref_cfg['port'] = int(cfg['port']) + 1
            require_free_loopback_port(ref_cfg['port'])
            ref_cfg['log'] = str((args.output.parent / 'reference-engine.log').resolve())
            ref_config = args.output.parent / 'reference-server-config.json'
            ref_config.write_text(json.dumps(ref_cfg, indent=2) + '\n')
            ref_base = f"http://127.0.0.1:{ref_cfg['port']}"
            reference = subprocess.Popen(
                [sys.executable, '-m', 'serve.server', '--engine', 'strata',
                 '--config', str(ref_config.resolve()), '--host', '127.0.0.1',
                 '--port', str(ref_cfg['port'])], cwd=ref_cfg['cwd'])
            try:
                ref_deadline = time.monotonic() + 300
                ref_health = None
                while time.monotonic() < ref_deadline:
                    if reference.poll() is not None:
                        raise RuntimeError(f'reference server exited: {reference.returncode}')
                    try:
                        with urllib.request.urlopen(ref_base + '/health', timeout=5) as response:
                            ref_health = json.load(response)
                        if ref_health.get('model'):
                            break
                    except (urllib.error.URLError, OSError, ValueError):
                        time.sleep(0.5)
                if not ref_health or not ref_health.get('model'):
                    raise TimeoutError('reference service readiness deadline')
                ref_body = dict(short_body, model=ref_health['model'])
                ref_response = post_json(ref_base + '/v1/chat/completions', ref_body)
                ref_content = ref_response['choices'][0]['message'].get('content', '').strip()
                ref_state = final_state(ref_cfg['log'])
                state_equal = all(recovery_state[k] == ref_state[k] for k in STATE_KEYS)
                result['recovery_state_comparison'] = {
                    'recovered_state': recovery_state,
                    'reference_state': ref_state,
                    'reference_answer': ref_content,
                    'all_fields_equal': state_equal,
                }
                recovery['state_comparison_status'] = 'pass' if state_equal and ref_content == content else 'fail'
                if not state_equal or ref_content != content:
                    recovery['reason'] += '; clean-service output/state comparison differed'
            finally:
                reference.terminate()
                try:
                    reference.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    reference.kill()
                    reference.wait(timeout=5)
        write_result(args.output, result)
        return int(recovery['status'] != 'pass' or
                   recovery.get('state_comparison_status', 'pass') != 'pass')
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
