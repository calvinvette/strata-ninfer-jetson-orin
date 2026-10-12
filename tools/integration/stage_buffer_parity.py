"""Compare pageable and pinned expert staging on one exact real-model prompt."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import statistics
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from conversation_cache_parity import load_tokenizer
from prepare_controls import exact_prompt, exact_prompt_variant
from owner_observations import summarize
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')
TIMING_INSTRUMENTATION_ENV_KEYS = ('STRATA_TRACE', 'STRATA_STATE_HASH',
                                   'STRATA_INTEGRATION_TRACE', 'STRATA_STATE_HASH_GDN',
                                   'LD_PRELOAD')


def stage_environment(env, pin, timing_only=False):
    """Configure one arm while keeping timed runs free of instrumentation."""
    env = dict(env)
    env['STRATA_STAGE_PIN'] = pin
    env['STRATA_MTP_BATCH'] = '1'
    env['STRATA_PREFILL_CPU_SHARE'] = '0'
    env['STRATA_IO_PREFETCH'] = '1'
    env['STRATA_IO_PF_STAGE'] = '1'
    if timing_only:
        for key in TIMING_INSTRUMENTATION_ENV_KEYS:
            env.pop(key, None)
    else:
        env.update({'STRATA_TRACE': '1', 'STRATA_STATE_HASH': '1',
                    'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_HASH_GDN': '1'})
    return env


def paired_ratio_effect(control, candidate, *, iterations=100000, seed=870126):
    """Median paired candidate/control latency delta and percentile bootstrap interval."""
    if len(control) != len(candidate) or not control or iterations < 1:
        raise ValueError('paired effects require equally sized nonempty samples and positive iterations')
    if any(value <= 0 for value in control + candidate):
        raise ValueError('paired latency values must be positive')
    effects = [(new / old - 1.0) * 100.0 for old, new in zip(control, candidate)]
    rng = random.Random(seed)
    boot = sorted(statistics.median(effects[rng.randrange(len(effects))] for _ in effects)
                  for _ in range(iterations))
    return {'paired_median_delta_pct': statistics.median(effects),
            'bootstrap_95pct_interval_pct': [boot[int((iterations - 1) * 0.025)],
                                             boot[int((iterations - 1) * 0.975)]],
            'pairs': len(effects), 'bootstrap_iterations': iterations,
            'pair_deltas_pct': effects}


def stamp_arm_start(arm):
    arm['started_wall_s'] = time.time()
    arm['started_monotonic_s'] = time.monotonic()


def stamp_arm_end(arm):
    arm['finished_wall_s'] = time.time()
    arm['finished_monotonic_s'] = time.monotonic()


def context_reservation(prompt_tokens, generated_tokens):
    """Leave room for Strata's strict prompt-plus-output context guard."""
    return max(prompt_tokens + generated_tokens + 32, 8192)


def state_hashes(path, expected_count=1):
    found = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if 'STATE_HASH L=' in line:
            fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
            if not set(STATE_KEYS) <= fields.keys():
                raise ValueError('incomplete persistent state fingerprint')
            found.append({key: fields[key] for key in STATE_KEYS})
    if len(found) != expected_count:
        raise ValueError(f'expected {expected_count} completed-request state fingerprints, got {len(found)}')
    return found[-1]


def warmup_completions_equal(pageable, pinned):
    """Whether both arms produced the same separately warmed completion."""
    left, right = pageable.get('warmup'), pinned.get('warmup')
    if left is None and right is None:
        return None
    if left is None or right is None:
        return False
    return (left.get('prompt_sha256') == right.get('prompt_sha256') and
            left.get('ids_sha256') == right.get('ids_sha256') and
            left.get('generated_tokens') == right.get('generated_tokens'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prompt-tokens', type=int, default=4096)
    parser.add_argument('--generated-tokens', type=int, default=64)
    parser.add_argument('--prompt-variant', choices=('primary', 'heldout_blue'), default='primary',
                        help='exact formatted prompt content; primary preserves the original control')
    parser.add_argument('--warmup-tokens', type=int, default=0,
                        help='optional distinct formatted request per process before measurement')
    parser.add_argument('--warmup-generated-tokens', type=int, default=64)
    parser.add_argument('--pairs', type=int, default=1)
    parser.add_argument('--seed', type=int, default=870126)
    parser.add_argument('--resume', action='store_true', help='continue an incomplete output directory after a harness interruption')
    parser.add_argument('--timing-only', action='store_true',
                        help='disable state/owner tracing; compare output IDs but do not claim state parity')
    parser.add_argument('--run', action='store_true', help='otherwise print the planned exact prompt size only')
    args = parser.parse_args()
    if args.prompt_tokens < 512 or args.generated_tokens < 8 or args.pairs < 1:
        parser.error('require prompt >=512, generation >=8 and pairs >=1')
    if args.warmup_tokens and (args.warmup_tokens < 1 or args.warmup_generated_tokens < 1):
        parser.error('warmup prompt and generation lengths must be positive')
    if args.output.exists() != args.resume:
        parser.error('use a new output directory, or pass --resume for an existing one')

    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    tokenizer = load_tokenizer(Path(cfg['tokenizer']))
    template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    render = lambda text: tokenizer.encode(
        template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
    prompt_text = exact_prompt_variant(args.prompt_tokens, render, args.prompt_variant)
    prompt = render(prompt_text)
    if len(prompt) != args.prompt_tokens:
        raise ValueError(f'formatted prompt has {len(prompt)} tokens, expected {args.prompt_tokens}')
    print(f'formatted prompt tokens: {len(prompt)}')
    warmup_prompt = []
    warmup_prompt_hash = None
    if args.warmup_tokens:
        warmup_text = exact_prompt(args.warmup_tokens, render)
        warmup_prompt = render(warmup_text)
        if len(warmup_prompt) != args.warmup_tokens:
            raise ValueError(f'formatted warmup has {len(warmup_prompt)} tokens, expected {args.warmup_tokens}')
        warmup_prompt_hash = hashlib.sha256(json.dumps(warmup_prompt, separators=(',', ':')).encode()).hexdigest()
        print(f'formatted warmup prompt tokens: {len(warmup_prompt)}')
    if not args.run:
        return 0

    with args.engine.open('rb') as binary:
        binary_hash = hashlib.file_digest(binary, 'sha256').hexdigest()
    result_path = args.output / 'results.json'
    prompt_hash = hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest()
    if args.resume:
        if not result_path.is_file():
            parser.error('resume directory has no results.json')
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if (result.get('prompt_sha256') != prompt_hash or
                result.get('prompt_variant', 'primary') != args.prompt_variant or
                result.get('generated_tokens') != args.generated_tokens or
                result.get('warmup_prompt_tokens', 0) != args.warmup_tokens or
                result.get('warmup_generated_tokens', 0) != (args.warmup_generated_tokens if args.warmup_tokens else 0) or
                result.get('warmup_prompt_sha256') != warmup_prompt_hash or
                result.get('planned_pairs') != args.pairs or result.get('seed') != args.seed or
                result.get('mode') != ('timing_only' if args.timing_only else 'traced_correctness_and_timing') or
                any(row.get('engine_sha256') != binary_hash for row in result.get('arms', []))):
            parser.error('resume inputs differ from the retained incomplete run')
        result['pair_comparisons'] = []
    else:
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        result = {'scope': 'exact real-model prompt, randomized paired staging diagnostic; screening only',
                  'mode': 'timing_only' if args.timing_only else 'traced_correctness_and_timing',
                  'prompt_variant': args.prompt_variant,
                  'prompt_tokens': len(prompt), 'prompt_sha256': prompt_hash,
                  'generated_tokens': args.generated_tokens, 'planned_pairs': args.pairs,
                  'warmup_prompt_tokens': args.warmup_tokens,
                  'warmup_generated_tokens': args.warmup_generated_tokens if args.warmup_tokens else 0,
                  'warmup_prompt_sha256': warmup_prompt_hash,
                  'seed': args.seed, 'arms': [], 'pair_comparisons': []}
    args_for = list(cfg['args'])
    for key, value in (('--max-context', str(context_reservation(args.prompt_tokens,
                                                                 args.generated_tokens))),
                       ('--prompt-cache', '6')):
        if key in args_for:
            args_for[args_for.index(key) + 1] = value
        else:
            args_for.extend([key, value])
    rng = random.Random(args.seed)
    modes = [('pageable', '0'), ('pinned', '1')]
    orders = []
    for _ in range(args.pairs):
        order = list(modes)
        rng.shuffle(order)
        orders.append(order)
    for pair in range(args.pairs):
        order = orders[pair]
        pair_rows = []
        for label, pin in order:
            existing = next((row for row in result['arms']
                             if row.get('pair') == pair and row.get('name') == label), None)
            if existing is not None:
                pair_rows.append(existing)
                continue
            log = args.output / f'pair-{pair}-{label}.log'
            if log.exists():
                parser.error(f'incomplete arm log exists without a terminal result: {log}')
            env = stage_environment(child_env(cfg), pin, args.timing_only)
            arm = {'pair': pair, 'name': label, 'stage_pin': pin, 'args': args_for,
                   'engine_sha256': binary_hash}
            stamp_arm_start(arm)
            engine = StrataEngine(str(args.engine.resolve()), args_for, cwd=cfg.get('cwd'),
                                  log=str(log), env=env)
            try:
                warmup = None
                if warmup_prompt:
                    warmup_ids = [token for token in engine.generate(
                        warmup_prompt, args.warmup_generated_tokens, {'temperature': 0}, threading.Event())
                        if token is not None]
                    warmup = {'prompt_tokens': len(warmup_prompt), 'generated_tokens': len(warmup_ids),
                              'requested_generated_tokens': args.warmup_generated_tokens,
                              'prompt_sha256': warmup_prompt_hash,
                              'ids_sha256': hashlib.sha256(json.dumps(
                                  warmup_ids, separators=(',', ':')).encode()).hexdigest()}
                ids = [token for token in engine.generate(prompt, args.generated_tokens,
                       {'temperature': 0}, threading.Event()) if token is not None]
                arm.update(ids=ids, text=tokenizer.decode(ids), usage=dict(engine.last), warmup=warmup)
            finally:
                try:
                    engine.close()
                finally:
                    stamp_arm_end(arm)
            if not args.timing_only:
                arm['state'] = state_hashes(log, 1 + (1 if args.warmup_tokens else 0))
                owners = summarize(log.read_text(encoding='utf-8').splitlines())
                arm['owner_observations'] = owners
                arm['stage_requested_bytes'] = {
                    row['owner']: row['peak_observed_requested_bytes'] for row in owners['owners']
                    if row['owner'] in ('expert-stage-pageable-host', 'expert-stage-pinned-host')}
            result['arms'].append(arm)
            pair_rows.append(arm)
            result_path.write_text(json.dumps(result, indent=2) + '\n')

        by_name = {row['name']: row for row in pair_rows}
        pageable, pinned = by_name['pageable'], by_name['pinned']
        failures = []
        warmup_equal = warmup_completions_equal(pageable, pinned)
        if warmup_equal is False:
            failures.append('warmup completion differs between staging arms')
        if pageable['ids'] != pinned['ids']:
            failures.append('generated token IDs differ')
        state_differences = []
        if not args.timing_only:
            state_differences = [key for key in STATE_KEYS if pageable['state'][key] != pinned['state'][key]]
            if state_differences:
                failures.append('persistent main-model state differs')
            if pageable['stage_requested_bytes'].get('expert-stage-pageable-host', 0) <= 0:
                failures.append('pageable stage backing was not observed')
            if pinned['stage_requested_bytes'].get('expert-stage-pinned-host', 0) <= 0:
                failures.append('pinned stage backing was not observed')
        result['pair_comparisons'].append({
            'pair': pair, 'order': [label for label, _ in order],
            'warmup_completion_equal': warmup_equal,
            'token_ids_equal': pageable['ids'] == pinned['ids'],
            'persistent_state_equal': None if args.timing_only else not state_differences,
            'differing_state_fields': state_differences, 'failures': failures})
        result_path.write_text(json.dumps(result, indent=2) + '\n')

    failures = sorted({failure for pair in result['pair_comparisons'] for failure in pair['failures']})
    result['summary'] = {}
    for label in ('pageable', 'pinned'):
        arms = [row for row in result['arms'] if row['name'] == label]
        result['summary'][label] = {}
        for key in ('prompt_ms', 'decode_ms'):
            result['summary'][label]['median_' + key] = statistics.median(
                row['usage'][key] for row in arms)
        if not args.timing_only:
            result['summary'][label]['stage_requested_bytes'] = statistics.median(
                row['stage_requested_bytes'].get('expert-stage-' + ('pageable' if label == 'pageable' else 'pinned') + '-host', 0)
                for row in arms)
    result['comparison'] = {'all_pairs_passed': not failures, 'failures': failures}
    pair_rows = {row['pair']: row for row in result['pair_comparisons']}
    metrics = {'prompt_ms': lambda arm: arm['usage']['prompt_ms'],
               'decode_ms': lambda arm: arm['usage']['decode_ms'],
               'request_ms': lambda arm: arm['usage']['prompt_ms'] + arm['usage']['decode_ms']}
    arms_by_pair = {}
    for arm in result['arms']:
        arms_by_pair.setdefault(arm['pair'], {})[arm['name']] = arm
    result['paired_effects'] = {}
    for metric, value_for in metrics.items():
        pairs = [arms_by_pair[index] for index in sorted(arms_by_pair)]
        effect = paired_ratio_effect([value_for(pair['pageable']) for pair in pairs],
                                     [value_for(pair['pinned']) for pair in pairs],
                                     seed=args.seed + sum(map(ord, metric)))
        result['paired_effects'][metric] = effect
        for row, delta in zip((pair_rows[index] for index in sorted(pair_rows)),
                              effect['pair_deltas_pct']):
            row.setdefault('paired_pinned_minus_pageable_pct', {})[metric] = delta
    result['passed'] = not failures
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    if failures:
        raise AssertionError('; '.join(failures))
    if args.timing_only:
        print('PASS: token IDs match; state and owner tracing were disabled for timing')
    else:
        print('PASS: token IDs and persistent state match; both stage backing modes observed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
