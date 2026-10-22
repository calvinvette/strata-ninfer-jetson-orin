"""Exercise --batch-mtp graph-layout eviction/recapture against serial controls."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from serve.server import StrataEngine, child_env  # noqa: E402
from serve.frontend import ChatTemplate  # noqa: E402
import strata_tokenizer as ST  # noqa: E402

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'pooled', 'kv', 'mtp', 'stale',
              'dead', 'pooled_full', 'ple_prev')
CAPTURE_RE = re.compile(r'captured the batch window over slots ([0-9,]+)')


def replace_arg(args: list[str], name: str, value: str) -> None:
    if name in args:
        args[args.index(name) + 1] = value
    else:
        args.extend((name, value))


def remove_arg(args: list[str], name: str) -> None:
    while name in args:
        index = args.index(name)
        del args[index:index + (2 if name != '--adapt-accepted-only' else 1)]


def state_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        marker = 'STATE_HASH '
        if marker not in line:
            continue
        fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line.split(marker, 1)[1]))
        if not set(STATE_KEYS) <= fields.keys():
            raise ValueError(f'incomplete persistent-state fingerprint in {path}: {fields}')
        rows.append({key: fields[key] for key in STATE_KEYS})
    return rows


def prepared_prompts(cfg: dict, count: int) -> dict[str, list[int]]:
    tokenizer_dir = Path(cfg['tokenizer'])
    vocab = json.loads((tokenizer_dir / 'vocab.json').read_text(encoding='utf-8'))
    tokens = [None] * len(vocab)
    for token, index in vocab.items():
        tokens[index] = token
    merges = (tokenizer_dir / 'merges.txt').read_text(encoding='utf-8').split('\n')
    types = json.loads((tokenizer_dir / 'token_type.json').read_text(encoding='utf-8'))
    tokenizer = ST.Tokenizer(tokens, merges, types)
    template = ChatTemplate(tokenizer_dir / 'chat_template.jinja')
    tasks = [
        'Write a Python function that returns the nth Fibonacci number, with one short example.',
        'Explain why a binary search needs sorted input, using a small concrete example.',
        'Write a Python function that removes duplicate strings while preserving their order.',
        'Give a concise checklist for debugging a program that intermittently times out.',
        'Write a SQL query that counts orders per customer and sorts by the count descending.',
        'Explain the difference between a process and a thread in two short paragraphs.',
        'Write a Python function that merges two sorted integer lists into one sorted list.',
        'Describe a simple test for checking whether a cache evicts its least recently used item.',
    ]
    prompts = {}
    for index, task in enumerate(tasks[:count]):
        rendered = template.render([{'role': 'user', 'content': task}], tools=None)
        prompts[f'slot-{index}'] = tokenizer.encode(rendered, parse_special=True)
    return prompts


def generate(engine: StrataEngine, prompt: list[int], max_tokens: int) -> dict:
    tokens = [token for token in engine.generate(prompt, max_tokens,
             {'temperature': 0}, threading.Event()) if token is not None]
    finish = engine.last.get('finish')
    if not tokens or finish not in ('length', 'stop'):
        raise RuntimeError(f'request {prompt} did not finish: tokens={tokens}, last={engine.last}')
    return {'prompt': prompt, 'tokens': tokens, 'finish': finish, 'usage': dict(engine.last)}


def run_serial(cfg: dict, args: list[str], env: dict, output: Path,
               prompts: dict[str, list[int]], max_tokens: int) -> dict:
    log = output / 'serial-engine.log'
    engine = StrataEngine(cfg['exe'], args, cwd=cfg.get('cwd'), log=str(log), env=env)
    try:
        if engine.batch:
            raise RuntimeError(f'serial control unexpectedly enabled {engine.batch} batch slots')
        result = {name: generate(engine, prompt, max_tokens) for name, prompt in prompts.items()}
    finally:
        engine.close()
    result['state_rows'] = state_rows(log)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--batch-slots', type=int, default=8)
    parser.add_argument('--max-tokens', type=int, default=96)
    parser.add_argument('--max-context', type=int, default=1024)
    parser.add_argument('--expert-cache-mib', type=int, default=1500)
    args = parser.parse_args()
    if not 2 <= args.batch_slots <= 8:
        parser.error('--batch-slots must be in 2..8')
    if args.max_tokens < 32 or args.max_context < args.max_tokens + 32:
        parser.error('use at least 32 output tokens and context >= max-tokens + 32')
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    engine_args = list(cfg['args'])
    replace_arg(engine_args, '--spec', '2')
    replace_arg(engine_args, '--max-context', str(args.max_context))
    replace_arg(engine_args, '--expert-cache', str(args.expert_cache_mib))
    replace_arg(engine_args, '--prompt-cache', '6')
    # The engine explicitly rejects adaptive accepted-only swaps with --batch-mtp.
    # Disable them in both arms so this checks batch graph/state behavior alone.
    remove_arg(engine_args, '--adapt-every')
    remove_arg(engine_args, '--adapt-accepted-only')
    env = child_env(cfg)
    env.update({'STRATA_INTEGRATION_TRACE': '1', 'STRATA_VERIFY_PROFILE': '1',
                'STRATA_STATE_HASH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    prompts = prepared_prompts(cfg, args.batch_slots)

    serial = run_serial(cfg, engine_args, env, args.output, prompts, args.max_tokens)
    batch_args = engine_args + ['--batch', str(args.batch_slots), '--batch-mtp']
    batch_log = args.output / 'batch-mtp-engine.log'
    engine = StrataEngine(cfg['exe'], batch_args, cwd=cfg.get('cwd'), log=str(batch_log), env=env)
    try:
        if engine.batch != args.batch_slots:
            raise RuntimeError(f'engine admitted {engine.batch} of {args.batch_slots} requested batch slots')
        with ThreadPoolExecutor(max_workers=args.batch_slots) as pool:
            futures = {name: pool.submit(generate, engine, prompt, args.max_tokens)
                       for name, prompt in prompts.items()}
            batch = {name: futures[name].result() for name in prompts}
    finally:
        engine.close()

    log_text = batch_log.read_text(encoding='utf-8', errors='replace')
    if 'WARNING: --batch-mtp is off:' in log_text:
        raise RuntimeError('engine disabled requested batch MTP')
    batch['state_rows'] = state_rows(batch_log)
    serial_outputs = {name: serial[name]['tokens'] for name in prompts}
    batch_outputs = {name: batch[name]['tokens'] for name in prompts}
    serial_states = Counter(tuple(sorted(row.items())) for row in serial['state_rows'])
    batch_states = Counter(tuple(sorted(row.items())) for row in batch['state_rows'])
    captured = CAPTURE_RE.findall(log_text)
    layout_counts = Counter(captured)
    recaptured = {layout: count for layout, count in layout_counts.items() if count > 1}
    checks = {
        'all_batch_slots_admitted': True,
        'batch_mtp_not_disabled': True,
        'all_outputs_match_serial': serial_outputs == batch_outputs,
        'all_terminal_state_fingerprints_match_serial': serial_states == batch_states,
        'one_terminal_state_per_request': len(serial['state_rows']) == args.batch_slots and
                                          len(batch['state_rows']) == args.batch_slots,
        'batch_graph_layouts_captured': len(captured),
        'unique_batch_graph_layouts': len(layout_counts),
        'recaptured_layouts': recaptured,
        'graph_eviction_and_recapture_observed': len(captured) > 64 and bool(recaptured),
    }
    result = {
        'config': str(args.config.resolve()), 'executable': cfg['exe'],
        'batch_slots': args.batch_slots, 'max_tokens_per_request': args.max_tokens,
        'max_context': args.max_context, 'expert_cache_mib': args.expert_cache_mib,
        'prompts': prompts, 'checks': checks,
        'serial': serial, 'batch_mtp': batch,
    }
    result['passed'] = all(value for key, value in checks.items()
                           if key not in ('batch_graph_layouts_captured',
                                           'unique_batch_graph_layouts', 'recaptured_layouts'))
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise AssertionError(json.dumps(checks, sort_keys=True))
    print(f"PASS: {args.batch_slots} batch-MTP slots; graph captures={len(captured)}, "
          f"unique={len(layout_counts)}, recaptured={len(recaptured)}; outputs and terminal state match serial")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
