"""Measure explicit prepared API workloads; preserve failed and incomplete cells."""
import argparse
import json
import math
from pathlib import Path
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request

from run_control import write_result


def request(base, route, body=None, *, timeout=3600):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + route, data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def stream_request(base, body):
    """Retain wire chunks; chunks are not assumed to be individual tokens."""
    start = time.monotonic()
    body = dict(body, stream=True)
    req = urllib.request.Request(base + '/v1/chat/completions',
                                 data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    events, text, reasoning = [], [], []
    final = {}
    first = None
    with urllib.request.urlopen(req, timeout=3600) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            payload = line[6:].strip()
            if payload == b'[DONE]':
                break
            obj = json.loads(payload)
            elapsed = time.monotonic() - start
            events.append({'elapsed_s': elapsed, 'event': obj})
            for choice in obj.get('choices', []):
                delta = choice.get('delta', {})
                if delta.get('content') or delta.get('reasoning_content'):
                    if first is None:
                        first = elapsed
                text.append(delta.get('content') or '')
                reasoning.append(delta.get('reasoning_content') or '')
            if obj.get('usage'):
                final.update(obj)
    final['choices'] = [{'message': {'content': ''.join(text),
                                    'reasoning_content': ''.join(reasoning)}}]
    return final, {'first_visible_delta_s': first, 'events': events,
                   'scope': 'client TTFT to first nonempty content/reasoning delta; chunk timestamps, not token timestamps'}


def qualify(row, expected):
    obj = row['response']
    usage, timings = obj.get('usage', {}), obj.get('timings', {})
    if usage.get('prompt_tokens') != expected['prompt_tokens']:
        return 'fail', 'formatted prompt count mismatch'
    if not usage.get('completion_tokens', 0):
        return 'fail', 'zero completion'
    if usage['completion_tokens'] != expected['generate_tokens']:
        return 'fail', 'early stop; requested workload not completed'
    if not timings or timings.get('cache_n', 0):
        return 'fail', 'missing timings or reused prompt; fresh-prefill control required'
    for key in ('prompt_per_second', 'predicted_per_second'):
        value = timings.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            return 'fail', f'missing or invalid stage rate: {key}'
    return 'pass', 'workload completed; not a numerical qualification'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:18081')
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variant', choices=['baseline', 'candidate'], required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--stream', action='store_true')
    parser.add_argument('--single-block', action='store_true', help='one measured repetition after warmup; caller supplies independent paired process blocks')
    args = parser.parse_args()
    url = urllib.parse.urlparse(args.base_url)
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.path not in ('', '/'):
        parser.error('use an explicit loopback HTTP server')
    if args.rounds < (1 if args.single_block else 3) or args.output.exists():
        parser.error('positive independent-block repetitions or >=3 screening repetitions, and a new output path required')
    health = request(args.base_url.rstrip('/'), '/health')
    workloads = json.loads(args.workloads.read_text())['workloads']
    rows = []
    result = {'variant': args.variant, 'health': health, 'checks': rows,
              'replication_scope': 'requests within one server process; screening only',
              'timing_scope': 'client total and API times (rounded); stream records client first-visible-delta TTFT when enabled',
              'qualification': 'no paired effect or speedup claimed by this single-variant adapter'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    failed = False
    for round_index in range(-1, args.rounds):
        for cell in workloads:
            row = {'cell': cell['cell'], 'round': round_index, 'warmup': round_index == -1,
                   'status': 'not_run', 'reason': 'request started', 'wall_time_s': time.time()}
            rows.append(row)
            write_result(args.output, result)
            body = {'model': health['model'], 'messages': cell['messages'],
                    'chat_template_kwargs': cell['chat_template_kwargs'],
                    'temperature': 0, 'max_tokens': cell['generate_tokens']}
            start = time.monotonic()
            row['request_start_monotonic_s'] = start
            try:
                if args.stream:
                    row['response'], row['stream_observation'] = stream_request(args.base_url.rstrip('/'), body)
                else:
                    row['response'] = request(args.base_url.rstrip('/'), '/v1/chat/completions', body)
                row['request_end_monotonic_s'] = time.monotonic()
                row['client_elapsed_s'] = row['request_end_monotonic_s'] - start
                row['status'], row['reason'] = qualify(row, cell)
                try:
                    row['metrics_after'] = request(args.base_url.rstrip('/'), '/metrics')
                except (urllib.error.URLError, ValueError, OSError) as exc:
                    row['metrics_error'] = str(exc)
            except (urllib.error.URLError, ValueError, OSError) as exc:
                row.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
            if 'client_elapsed_s' not in row:
                row['client_elapsed_s'] = time.monotonic() - start
            failed |= row['status'] != 'pass'
            write_result(args.output, result)
            print(row['cell'], round_index, row['status'], row['reason'], flush=True)
    result['summary'] = []
    for cell in workloads:
        measured = [r for r in rows if r['cell'] == cell['cell'] and not r['warmup'] and r['status'] == 'pass']
        summary = {'cell': cell['cell'], 'passed_samples': len(measured), 'planned_samples': args.rounds}
        for key in ('prompt_per_second', 'predicted_per_second'):
            values = [r['response']['timings'].get(key) for r in measured]
            if values and all(isinstance(v, (int, float)) and v > 0 for v in values):
                summary['median_' + key] = statistics.median(values)
        result['summary'].append(summary)
    write_result(args.output, result)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
