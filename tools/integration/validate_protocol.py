"""Durable real-model protocol scenarios from the inherited Orin validation.

Adapted from bench/results/2026-10-08-jetson-orin/validate_api.py (Strata MIT),
preserving seven scenarios while retaining each started/failed/finished result.
"""
import argparse
import json
from pathlib import Path
import time

import requests

from run_control import write_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:18081')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.base_url.startswith('http://127.0.0.1:') or args.out.exists():
        parser.error('explicit loopback URL and a new output path required')
    model = requests.get(args.base_url + '/health', timeout=10).json()['model']
    body = {'model': model, 'messages': [{'role': 'user', 'content': 'Reply with exactly: Hello Orin!'}],
            'temperature': 0, 'max_tokens': 24, 'chat_template_kwargs': {'enable_thinking': False}}
    result = {'scope': 'real-model protocol/cancellation recovery; not persistent-state parity', 'checks': []}
    args.out.parent.mkdir(parents=True, exist_ok=True)

    def post(row):
        start = time.monotonic()
        response = requests.post(args.base_url + '/v1/chat/completions', json=body, timeout=120)
        response.raise_for_status()
        row['response'] = response.json()
        row['client_elapsed_s'] = time.monotonic() - start
        assert row['response']['usage']['completion_tokens'] > 0
        assert row['response']['choices'][0]['message']['content'].strip() == 'Hello Orin!', row['response']

    def streaming(row, anthropic=False):
        request = dict(body, stream=True)
        route = '/v1/chat/completions'
        if anthropic:
            request.pop('chat_template_kwargs')
            request['thinking'] = {'type': 'disabled'}
            route = '/v1/messages'
        row['events'], text = [], ''
        with requests.post(args.base_url + route, json=request, stream=True, timeout=120,
                           headers={'anthropic-version': '2023-06-01'}) as response:
            response.raise_for_status()
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line or not line.startswith('data: ') or line == 'data: [DONE]':
                    continue
                obj = json.loads(line[6:])
                row['events'].append(obj)
                if anthropic and obj.get('type') == 'content_block_delta':
                    text += obj.get('delta', {}).get('text', '')
                elif not anthropic and obj.get('choices'):
                    text += obj['choices'][0].get('delta', {}).get('content') or ''
        row['text'] = text
        assert text.strip() == 'Hello Orin!', text

    def cancel(row, phase):
        text = 'Count from 1 to 100 separated by commas.'
        if phase == 'prefill':
            text = 'Read this context, then answer OK: ' + 'red green blue yellow ' * 256
        request = dict(body, stream=True, max_tokens=256, messages=[{'role': 'user', 'content': text}])
        start = time.monotonic()
        with requests.post(args.base_url + '/v1/chat/completions', json=request, stream=True, timeout=120) as response:
            response.raise_for_status()
            if phase == 'decode':
                seen = False
                for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                    if line and line.startswith('data: ') and line != 'data: [DONE]':
                        obj = json.loads(line[6:])
                        if obj.get('choices') and obj['choices'][0].get('delta', {}).get('content'):
                            seen = True
                            break
                assert seen, 'no visible decode content before cancellation'
            else:
                time.sleep(0.5)
        row['time_until_close_s'] = time.monotonic() - start
        recovery = {}
        row['recovery'] = recovery
        post(recovery)

    scenarios = [(f'repeated_greedy_{i}', post) for i in range(3)]
    scenarios += [('openai_stream', streaming), ('anthropic_stream', lambda r: streaming(r, True)),
                  ('cancel_decode', lambda r: cancel(r, 'decode')), ('cancel_prefill', lambda r: cancel(r, 'prefill'))]
    for name, action in scenarios:
        row = {'check': name, 'status': 'not_run', 'reason': 'started', 'wall_time_s': time.time()}
        result['checks'].append(row)
        write_result(args.out, result)
        try:
            action(row)
            row.update(status='pass', reason='scenario completed')
        except Exception as exc:
            row.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
        write_result(args.out, result)
        print(name, row['status'], row['reason'], flush=True)
    return int(any(row['status'] != 'pass' for row in result['checks']))


if __name__ == '__main__':
    raise SystemExit(main())
