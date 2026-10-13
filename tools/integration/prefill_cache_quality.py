"""Run a full-length task-quality check over a cache × prefill grid."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

from cache_context_screen import replace_option


def api_json(base, route, body=None, timeout=3600):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + route, data=data,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def rubric(text):
    words = text.split()
    lower = text.lower()
    checks = {
        'starts_processor': text.lstrip().startswith('Processor:'),
        'at_least_200_words': len(words) >= 200,
        'fetch_decode_execute': all(word in lower for word in ('fetch', 'decode', 'execute')),
        'ram': 'ram' in lower,
        'binary_data': 'binary' in lower,
        'input_output': 'input' in lower and 'output' in lower,
        'exact_arithmetic': '17 x 19 = 323' in text,
    }
    return checks, len(words)


def run_cell(config, workload, output, python):
    output.mkdir()
    cfg = dict(config)
    cfg['port'] = int(config['port'])
    cfg['log'] = str((output / 'engine.log').resolve())
    cfg['env'] = dict(cfg.get('env', {}))
    for key in ('STRATA_TRACE', 'STRATA_STATE_HASH', 'STRATA_STATE_HASH_GDN',
                'STRATA_INTEGRATION_TRACE', 'STRATA_ACCEPTED_PREFIX_TRACE'):
        cfg['env'].pop(key, None)
    server_env = os.environ.copy()
    server_env.update({str(key): str(value) for key, value in cfg['env'].items()})
    cfgpath = output / 'server-config.json'
    cfgpath.write_text(json.dumps(cfg, indent=2) + '\n')
    base = f"http://127.0.0.1:{cfg['port']}"
    process = subprocess.Popen([python, '-m', 'serve.server', '--engine', 'strata',
                                '--config', str(cfgpath.resolve()), '--host', '127.0.0.1',
                                '--port', str(cfg['port'])], cwd=cfg['cwd'], env=server_env,
                               stdout=(output / 'server.stdout').open('w'),
                               stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 240
        while True:
            if process.poll() is not None:
                raise RuntimeError(f'server exited during startup: {process.returncode}')
            try:
                health = api_json(base, '/health', timeout=5)
                if health.get('model'):
                    break
            except (urllib.error.URLError, OSError):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError('server readiness timeout')
            time.sleep(.5)
        prompt = workload['messages']
        response = api_json(base, '/v1/chat/completions', {
            'model': health['model'], 'messages': prompt,
            'chat_template_kwargs': workload['chat_template_kwargs'],
            'temperature': 0, 'max_tokens': 512,
        })
        (output / 'response.json').write_text(json.dumps(response, indent=2) + '\n')
        message = response['choices'][0]['message']
        content = message.get('content', '') or ''
        checks, count = rubric(content)
        result = {'status': 'pass' if all(checks.values()) else 'fail',
                  'word_count': count, 'rubric': checks,
                  'finish_reason': response['choices'][0].get('finish_reason'),
                  'usage': response.get('usage'), 'timings': response.get('timings'),
                  'metrics': api_json(base, '/metrics')}
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache-values', type=int, nargs='+', default=[3000, 5000])
    parser.add_argument('--prefill-values', type=int, nargs='+', default=[32, 128])
    parser.add_argument('--python', default=sys.executable)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    workloads = json.loads(args.workloads.read_text())['workloads']
    if len(workloads) != 1 or args.output.exists():
        parser.error('one prepared task and a new output directory are required')
    args.output.mkdir(parents=True)
    rows = []
    for cache in args.cache_values:
        for prefill in args.prefill_values:
            name = f'cache{cache}-prefill{prefill}'
            cell_config = dict(config, args=replace_option(
                replace_option(config['args'], '--expert-cache', cache), '--prefill', prefill))
            row = {'cell': name, 'expert_cache_argument': cache,
                   'prefill_chunk_tokens': prefill}
            try:
                row.update(run_cell(cell_config, workloads[0], args.output / name, args.python))
            except Exception as exc:
                row.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
            rows.append(row)
            (args.output / 'campaign.json').write_text(json.dumps({'cells': rows}, indent=2) + '\n')
            print(name, row['status'], row.get('word_count'), flush=True)
            if row['status'] != 'pass':
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
