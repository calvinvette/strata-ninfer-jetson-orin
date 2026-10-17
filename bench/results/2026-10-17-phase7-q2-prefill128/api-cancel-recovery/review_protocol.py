#!/usr/bin/env python3
"""Independently review the selected-profile seven-scenario protocol output."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    checks = result.get('protocol', {}).get('checks', [])
    names = ['repeated_greedy_0', 'repeated_greedy_1', 'repeated_greedy_2',
             'openai_stream', 'anthropic_stream', 'cancel_decode', 'cancel_prefill']
    by_name = {row.get('check'): row for row in checks}
    required = {name: by_name.get(name, {}).get('status') == 'pass' for name in names}
    recovery = {}
    for name in ('cancel_decode', 'cancel_prefill'):
        text = (by_name.get(name, {}).get('recovery', {}).get('response', {})
                .get('choices', [{}])[0].get('message', {}).get('content', '').strip())
        recovery[name] = text == 'Hello Orin!'
    engine_log = Path(args.result).parent / 'server.log'
    log_text = engine_log.read_text(errors='replace') if engine_log.exists() else ''
    review = {
        'overall_pass': result.get('status') == 'pass' and all(required.values())
            and all(recovery.values()) and log_text.count('cancel=True') >= 2,
        'seven_scenarios_pass': required,
        'same_service_recovery_exact': recovery,
        'engine_cancel_records': log_text.count('cancel=True'),
        'active_prefill_progress_proven': False,
        'boundary': 'prefill disconnect was logged, but active prompt progress was not retained for that case',
    }
    args.output.write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps(review, indent=2))
    return 0 if review['overall_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
