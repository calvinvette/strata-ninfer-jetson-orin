#!/usr/bin/env python3
"""Independent assertions for an observed-progress prefill disconnect."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    cancel = result.get('cancel', {})
    recovery = result.get('recovery', {})
    checks = {
        'runner_pass': result.get('status') == 'pass',
        'context_8192': result.get('configured_context') == 8192,
        'expected_long_prompt': result.get('expected_prompt_tokens') == 7498,
        'engine_observed_prefill_before_disconnect':
            0 < cancel.get('engine_progress_tokens_before_disconnect', 0)
            < result.get('expected_prompt_tokens', 0),
        'engine_confirmed_cancel': 'cancel=True' in cancel.get('cancel_record', ''),
        'same_service_recovery': recovery.get('status') == 'pass'
            and recovery.get('answer') == 'Hello Orin!',
        'server_stopped': result.get('server_returncode_after_stop') is not None,
    }
    review = {'overall_pass': all(checks.values()), 'checks': checks,
              'prefill_progress_record': cancel.get('engine_progress_record'),
              'cancel_record': cancel.get('cancel_record'),
              'recovery': recovery}
    args.output.write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps(review, indent=2))
    return 0 if review['overall_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
