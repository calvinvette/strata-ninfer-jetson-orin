#!/usr/bin/env python3
"""Compare repeated 1,069-token temperature-zero requests across Q2_0 miss routes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import parse_hashes
from conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

BASE_CONFIG = ROOT / 'bench/results/2026-10-25-q2-current-candidate-performance/server-config.template.json'
WORKLOADS = ROOT / 'bench/results/2026-10-09-paired-api-controls/extension/block-3-workloads.json'
ENGINE = ROOT / 'build/integration/e0-cuda-build/strata'
STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
ARMS = ('cpu-miss', 'ninfer-staged')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new output directory')
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--fresh-each', action='store_true',
                        help='start a fresh engine for each repeat instead of reusing one process')
    parser.add_argument('--prompt-cache', type=int, choices=(0, 6), default=6)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error('--repeats must be at least 2')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(BASE_CONFIG.read_text())
    workloads = json.loads(WORKLOADS.read_text())['workloads']
    workload = next(row for row in workloads if row['cell'] == 'historical-repeat-256')
    tokenizer = load_tokenizer(Path(cfg['tokenizer']))
    template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
    template = ChatTemplate(template_path)
    prompt = tokenizer.encode(template.render(workload['messages'], enable_thinking=False), parse_special=True)
    if len(prompt) != 1069:
        raise ValueError(f'expected 1,069 formatted prompt tokens, got {len(prompt)}')

    base_args = list(cfg['args'])
    overrides = {'--max-context': '8192', '--prompt-cache': str(args.prompt_cache), '--pcie-frac': '0.0'}
    for flag, value in overrides.items():
        if flag in base_args:
            base_args[base_args.index(flag) + 1] = value
        else:
            base_args.extend([flag, value])
    records = []
    for arm in ARMS:
        engine_args = list(base_args)
        if arm == 'ninfer-staged':
            engine_args[engine_args.index('--pcie-frac') + 1] = '1.0'
            engine_args.extend(['--expert-backend', 'ninfer', '--expert-backend-strict'])
        env = child_env(cfg)
        env.update({'STRATA_STATE_HASH': '1', 'STRATA_INTEGRATION_TRACE': '1',
                    'STRATA_MTP_BATCH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
        arm_rows = []
        repeats_per_engine = 1 if args.fresh_each else args.repeats
        for engine_group in range(args.repeats // repeats_per_engine):
            log_path = out / (f'{arm}-repeat-{engine_group}.log' if args.fresh_each else f'{arm}.log')
            engine = StrataEngine(str(ENGINE), engine_args, cwd=cfg.get('cwd'),
                                  log=str(log_path), env=env)
            try:
                for _ in range(repeats_per_engine):
                    repeat = len(arm_rows)
                    token_ids = [token for token in engine.generate(
                        prompt, 64, {'temperature': 0}, threading.Event()) if token is not None]
                    last = dict(engine.last)
                    if len(token_ids) != 64:
                        raise RuntimeError(f'{arm} repeat {repeat}: generated {len(token_ids)} tokens')
                    if last.get('drafts_offered') != 0 or last.get('drafts_accepted') != 0:
                        raise RuntimeError(f'{arm} repeat {repeat}: unexpected MTP draft counts {last}')
                    row = {'arm': arm, 'repeat': repeat, 'token_ids': token_ids,
                           'text': tokenizer.decode(token_ids), 'last': last}
                    arm_rows.append(row)
                    records.append(row)
            finally:
                engine.close()
            state_rows = parse_hashes(log_path)
            if args.prompt_cache > 0 and len(state_rows) != repeats_per_engine:
                raise RuntimeError(f'{arm}: expected {repeats_per_engine} state fingerprints in {log_path}, got {len(state_rows)}')
            first = len(arm_rows) - repeats_per_engine
            for idx, row in enumerate(arm_rows[first:]):
                row['state'] = state_rows[idx] if idx < len(state_rows) else None

    for row in records:
        row['output_sha256'] = hashlib.sha256(
            json.dumps(row['token_ids'], separators=(',', ':')).encode()).hexdigest()
    cpu = [row for row in records if row['arm'] == 'cpu-miss']
    staged = [row for row in records if row['arm'] == 'ninfer-staged']
    summary = {
        'prompt_tokens': len(prompt),
        'prompt_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
        'repeats': args.repeats,
        'within_arm': {},
        'cross_arm': {'token_ids_equal_per_repeat': [], 'state_equal_per_repeat': []},
    }
    for arm, rows in (('cpu-miss', cpu), ('ninfer-staged', staged)):
        summary['within_arm'][arm] = {
            'token_ids_equal': all(row['token_ids'] == rows[0]['token_ids'] for row in rows[1:]),
            'state_equal': (None if any(row['state'] is None for row in rows) else
                            all(all(row['state'].get(k) == rows[0]['state'].get(k)
                                    for k in STATE_KEYS) for row in rows[1:])),
            'output_sha256': [row['output_sha256'] for row in rows],
            'differing_state_fields_from_first': (None if any(row['state'] is None for row in rows) else
                [k for k in STATE_KEYS
                 if any(row['state'].get(k) != rows[0]['state'].get(k) for row in rows[1:])]),
        }
    for left, right in zip(cpu, staged):
        summary['cross_arm']['token_ids_equal_per_repeat'].append(left['token_ids'] == right['token_ids'])
        summary['cross_arm']['state_equal_per_repeat'].append(
            None if left['state'] is None or right['state'] is None else
            all(left['state'].get(k) == right['state'].get(k) for k in STATE_KEYS))
    result = {'source_commit': __import__('subprocess').check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'binary_sha256': hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
              'cache_policy': (f'prompt-cache {args.prompt_cache}; fresh engine per request' if args.fresh_each else
                               f'prompt-cache {args.prompt_cache}; repeated same prompt in one engine process'),
              'temperature': 0, 'mtp_drafts_required': 0,
              'diagnostic': summary, 'runs': records}
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'diagnostic': summary}, indent=2))


if __name__ == '__main__':
    main()
