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
    overrides = {'--max-context': '8192', '--prompt-cache': '6', '--pcie-frac': '0.0'}
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
        log_path = out / f'{arm}.log'
        engine = StrataEngine(str(ENGINE), engine_args, cwd=cfg.get('cwd'),
                              log=str(log_path), env=env)
        try:
            for repeat in range(args.repeats):
                token_ids = [token for token in engine.generate(
                    prompt, 64, {'temperature': 0}, threading.Event()) if token is not None]
                last = dict(engine.last)
                if len(token_ids) != 64:
                    raise RuntimeError(f'{arm} repeat {repeat}: generated {len(token_ids)} tokens')
                if last.get('drafts_offered') != 0 or last.get('drafts_accepted') != 0:
                    raise RuntimeError(f'{arm} repeat {repeat}: unexpected MTP draft counts {last}')
                records.append({'arm': arm, 'repeat': repeat, 'token_ids': token_ids,
                                'text': tokenizer.decode(token_ids), 'last': last})
        finally:
            engine.close()
        state_rows = parse_hashes(log_path)
        arm_rows = [row for row in records if row['arm'] == arm]
        if len(state_rows) != args.repeats:
            raise RuntimeError(f'{arm}: expected {args.repeats} state fingerprints, got {len(state_rows)}')
        for row, state in zip(arm_rows, state_rows):
            row['state'] = state

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
            'state_equal': all(all(row['state'].get(k) == rows[0]['state'].get(k)
                                   for k in STATE_KEYS) for row in rows[1:]),
            'output_sha256': [row['output_sha256'] for row in rows],
            'differing_state_fields_from_first': [k for k in STATE_KEYS
                if any(row['state'].get(k) != rows[0]['state'].get(k) for row in rows[1:])],
        }
    for left, right in zip(cpu, staged):
        summary['cross_arm']['token_ids_equal_per_repeat'].append(left['token_ids'] == right['token_ids'])
        summary['cross_arm']['state_equal_per_repeat'].append(
            all(left['state'].get(k) == right['state'].get(k) for k in STATE_KEYS))
    result = {'source_commit': __import__('subprocess').check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'binary_sha256': hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
              'cache_policy': 'prompt-cache 6; repeated same prompt in one engine process',
              'temperature': 0, 'mtp_drafts_required': 0,
              'diagnostic': summary, 'runs': records}
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'diagnostic': summary}, indent=2))


if __name__ == '__main__':
    main()
