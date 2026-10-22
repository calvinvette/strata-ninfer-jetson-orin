#!/usr/bin/env python3
"""Drive staggered batch-MTP requests until the production 64-layout LRU evicts."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools' / 'integration')]
from serve.server import StrataEngine, child_env  # noqa: E402
from batch_mtp_graph_lifecycle import generate, prepared_prompts, remove_arg, replace_arg  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--requests', type=int, default=80)
    args = parser.parse_args()
    if args.requests < 65:
        parser.error('--requests must be at least 65')
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    engine_args = list(cfg['args'])
    replace_arg(engine_args, '--spec', '2')
    replace_arg(engine_args, '--max-context', '8192')
    replace_arg(engine_args, '--expert-cache', '1500')
    replace_arg(engine_args, '--prompt-cache', '0')
    remove_arg(engine_args, '--adapt-every')
    remove_arg(engine_args, '--adapt-accepted-only')
    batch_args = engine_args + ['--batch', '8', '--batch-mtp']
    env = child_env(cfg)
    env.pop('STRATA_BATCH_MTP_GRAPH_LIMIT', None)
    env.update({'STRATA_INTEGRATION_TRACE': '1', 'STRATA_VERIFY_PROFILE': '1',
                'STRATA_STATE_HASH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    prompts = prepared_prompts(cfg, 8)
    pattern = (32, 96, 48, 80, 40, 64, 56, 88)
    jobs = []
    for index in range(args.requests):
        name = f'request-{index:03d}'
        prompt_name = f'slot-{(index * 5 + index // 8) % len(prompts)}'
        jobs.append((name, prompt_name, prompts[prompt_name], pattern[index % len(pattern)]))

    log = args.output / 'batch-mtp-engine.log'
    engine = StrataEngine(cfg['exe'], batch_args, cwd=cfg.get('cwd'), log=str(log), env=env)
    results = {}
    try:
        if engine.batch != 8:
            raise RuntimeError(f'engine admitted {engine.batch} of 8 requested batch slots')
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(generate, engine, prompt, limit): (name, prompt_name, limit)
                for name, prompt_name, prompt, limit in jobs
            }
            for future in as_completed(futures):
                name, prompt_name, limit = futures[future]
                response = future.result()
                results[name] = {
                    'prompt_name': prompt_name,
                    'prompt_sha256': hashlib.sha256(
                        json.dumps(jobs[int(name[-3:])][2], separators=(',', ':')).encode()).hexdigest(),
                    'max_tokens': limit,
                    'token_count': len(response['tokens']),
                    'token_ids': response['tokens'],
                }
    finally:
        engine.close()

    log_text = log.read_text(encoding='utf-8', errors='replace')
    captures = re.findall(r'captured the batch window over slots ([0-9,]+)', log_text)
    layouts = {layout for layout in captures}
    evictions = log_text.count('evicted least-recently-used batch graph layout')
    limit_messages = re.findall(r'batch-MTP graph layout limit (\d+)([^\n]*)', log_text)
    result = {
        'config': str(args.config.resolve()),
        'executable': cfg['exe'],
        'requests_submitted': args.requests,
        'requests_completed': len(results),
        'batch_slots': engine.batch,
        'default_graph_limit_log': limit_messages,
        'graph_capture_count': len(captures),
        'unique_layout_count': len(layouts),
        'layout_limit_crossed': len(layouts) > 64,
        'eviction_count': evictions,
        'eviction_observed': evictions > 0,
        'all_requests_completed': len(results) == args.requests,
        'requests': results,
    }
    result['passed'] = (result['all_requests_completed'] and result['layout_limit_crossed'] and
                        result['eviction_observed'] and
                        any(limit == '64' and not suffix for limit, suffix in limit_messages))
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'requests'}, indent=2))
    if not result['passed']:
        raise RuntimeError('default-cap stress did not complete all requests and observe 64-layout eviction')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
