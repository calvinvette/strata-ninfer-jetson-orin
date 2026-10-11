"""Compare one-token serial and concurrent --batch requests while tracing slot owners."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env  # noqa: E402

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')


def hashes(path: Path) -> list[dict[str, str]]:
    result = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if 'STATE_HASH L=' not in line:
            continue
        fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
        if not set(STATE_KEYS) <= fields.keys():
            raise ValueError(f'incomplete persistent state hash in {path}')
        result.append({key: fields[key] for key in STATE_KEYS})
    return result


def run_one(engine: StrataEngine, ids: list[int]) -> dict:
    output = [token for token in engine.generate(ids, 1, {'temperature': 0}, threading.Event())
              if token is not None]
    if len(output) != 1 or engine.last.get('finish') not in ('length', 'stop'):
        raise RuntimeError(f'request {ids} did not finish one token: {output}, {engine.last}')
    return {'input': ids, 'output': output, 'usage': dict(engine.last)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    engine_args = list(cfg['args'])
    for key, value in (('--prompt-cache', '6'), ('--spec', '2')):
        if key in engine_args:
            engine_args[engine_args.index(key) + 1] = value
        else:
            engine_args.extend([key, value])
    env = child_env(cfg)
    env.update({'STRATA_INTEGRATION_TRACE': '1', 'STRATA_VERIFY_PROFILE': '1',
                'STRATA_STATE_HASH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    prompts = {'a': [32], 'b': [33]}
    results: dict = {'prompts': prompts, 'baseline': {}, 'batch': {}}

    baseline_log = args.output / 'baseline-engine.log'
    baseline = StrataEngine(cfg['exe'], engine_args, cwd=cfg.get('cwd'), log=str(baseline_log), env=env)
    try:
        if baseline.batch:
            raise RuntimeError(f'baseline unexpectedly enabled {baseline.batch} batch slots')
        for name, ids in prompts.items():
            results['baseline'][name] = run_one(baseline, ids)
    finally:
        baseline.close()
    results['baseline']['states'] = hashes(baseline_log)

    batch_args = engine_args + ['--batch', '2']
    batch_log = args.output / 'batch-engine.log'
    batched = StrataEngine(cfg['exe'], batch_args, cwd=cfg.get('cwd'), log=str(batch_log), env=env)
    try:
        if batched.batch != 2:
            raise RuntimeError(f'engine admitted {batched.batch} of 2 requested batch slots')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {name: pool.submit(run_one, batched, ids) for name, ids in prompts.items()}
            for name, future in futures.items():
                results['batch'][name] = future.result()
    finally:
        batched.close()
    results['batch']['states'] = hashes(batch_log)

    outputs_by_request = lambda arm: {name: arm[name]['output'] for name in prompts}
    same_outputs = outputs_by_request(results['baseline']) == outputs_by_request(results['batch'])

    def states_by_prompt(arm: dict) -> dict[str, tuple[str, ...]]:
        mapped = {}
        for row in arm['states']:
            prompt_id = row['ple_prev'].split(',')[-1]
            if prompt_id in mapped:
                raise ValueError(f'duplicate state fingerprint for prompt token {prompt_id}')
            mapped[prompt_id] = tuple(row[key] for key in STATE_KEYS)
        return mapped

    baseline_states = states_by_prompt(results['baseline'])
    batch_states = states_by_prompt(results['batch'])
    expected_prompts = {str(ids[0]) for ids in prompts.values()}
    same_state_by_prompt = (set(baseline_states) == expected_prompts and
                            set(batch_states) == expected_prompts and
                            baseline_states == batch_states)
    results['checks'] = {'two_slots_admitted': True, 'outputs_match_serial': same_outputs,
                         'persistent_state_matches_by_prompt': same_state_by_prompt,
                         'baseline_state_count': len(results['baseline']['states']),
                         'batch_state_count': len(results['batch']['states'])}
    results['passed'] = (same_outputs and same_state_by_prompt and
                         len(results['baseline']['states']) == 2 and len(results['batch']['states']) == 2)
    (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    if not results['passed']:
        raise AssertionError(json.dumps(results['checks'], sort_keys=True))
    print('PASS: two batch slots admitted; concurrent outputs and persistent-state hashes match serial controls')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
