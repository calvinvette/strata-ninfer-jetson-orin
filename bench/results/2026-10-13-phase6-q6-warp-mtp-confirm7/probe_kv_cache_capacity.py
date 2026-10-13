#!/usr/bin/env python3
"""Read the actual expert-cache slot count before an elastic-KV request."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from serve.server import StrataEngine, child_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--expert-cache-mib', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.read_text())
    argv = list(config['args'])
    argv[argv.index('--expert-cache') + 1] = str(args.expert_cache_mib)
    argv[argv.index('--max-context') + 1] = '16384'
    argv.append('--kv-grow')
    env = child_env(config)
    env.update({'STRATA_KV_GROW_INIT': '2048', 'STRATA_KV_GROW_STEP': '2048',
                'STRATA_PREFILL_CPU_SHARE': '0'})
    log = args.output / 'engine.log'
    engine = StrataEngine(config['exe'], argv, cwd=config['cwd'], log=str(log), env=env)
    info = dict(engine.info)
    engine.close()
    text = log.read_text(errors='replace')
    match = re.search(r'expert cache (\d+) slots', text)
    grow = re.search(r'elastic K/V: (\d+) of (\d+) cells', text)
    result = {'expert_cache_mib_setting': args.expert_cache_mib,
              'actual_expert_cache_slots': int(match.group(1)) if match else None,
              'kv_cells': [int(grow.group(1)), int(grow.group(2))] if grow else None,
              'engine_info': info,
              'engine_sha256': hashlib.sha256(Path(config['exe']).read_bytes()).hexdigest()}
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if match and grow else 1


if __name__ == '__main__':
    raise SystemExit(main())
