#!/usr/bin/env python3
"""Freeze an adapted Q2_0 expert residency profile and replay the recovery prompt."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.conversation_cache_parity import load_tokenizer
from tools.integration.pool_worker_screen import read_accepted_prefix_trace
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')


def encode(workload, tokenizer, template):
    rendered = template.render(workload['messages'], enable_thinking=False)
    tokens = tokenizer.encode(rendered, parse_special=True)
    if len(tokens) != workload['prompt_tokens']:
        raise ValueError(f"{workload['cell']}: expected {workload['prompt_tokens']}, encoded {len(tokens)}")
    return [int(token) for token in tokens]


def run_one(engine, log_path, name, prompt, tokenizer, expected, prior_rows):
    generated = [int(token) for token in engine.generate(prompt, 48, {'temperature': 0}, threading.Event())
                 if token is not None]
    answer = tokenizer.decode(generated).strip().removesuffix('<|im_end|>').rstrip()
    trace_rows = read_accepted_prefix_trace(log_path)
    trace = trace_rows[prior_rows:]
    if not trace:
        raise ValueError(f'{name}: no accepted-prefix state trace')
    traced = [token for row in trace for token in row['token_ids']]
    if traced != generated:
        raise ValueError(f'{name}: state trace IDs differ from emitted token IDs')
    state = trace[-1]['state']
    if not set(STATE_KEYS).issubset(state):
        raise ValueError(f'{name}: state trace is missing persistent fields')
    result = {
        'name': name, 'token_ids': generated,
        'token_ids_sha256': hashlib.sha256(json.dumps(generated).encode()).hexdigest(),
        'answer': answer, 'answer_sha256': hashlib.sha256(answer.encode()).hexdigest(),
        'completion_tokens': len(generated), 'finish': engine.last.get('finish'),
        'usage': engine.last, 'quality_pass': answer == expected,
        'state': state, 'accepted_prefix_rows': len(trace),
        'accepted_prefix_trace': trace,
    }
    return result, len(trace_rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--short-workload', type=Path, required=True)
    ap.add_argument('--long-workload', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text())
    tok_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tok_path)
    template_path = tok_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    short = json.loads(args.short_workload.read_text())['workloads'][0]
    long = json.loads(args.long_workload.read_text())['workloads'][0]
    short_ids = encode(short, tokenizer, template)
    long_ids = encode(long, tokenizer, template)
    codes = short['expected_codes']
    expected_sum = short['expected_sum']
    if codes != long['expected_codes'] or expected_sum != long['expected_sum']:
        raise ValueError('short/long task oracles differ')
    if sum(int(code.rsplit('-', 1)[1]) for code in codes) != expected_sum:
        raise ValueError('suffix-sum oracle is invalid')
    expected = (f'EARLY={codes[0]}, MIDDLE={codes[1]}, LATE={codes[2]}, '
                f'SUM={expected_sum}')

    result = {
        'scope': 'Q2_0 dynamic adaptive residency followed by static replay using saved final resident profile',
        'sequence': ['short-8192', 'long-16384', 'short-8192-recovery',
                     'frozen-profile-short-1', 'frozen-profile-short-2'],
        'expected_answer': expected,
        'prompt_tokens': {'short': len(short_ids), 'long': len(long_ids)},
        'prompt_token_sha256': {
            'short': hashlib.sha256(json.dumps(short_ids).encode()).hexdigest(),
            'long': hashlib.sha256(json.dumps(long_ids).encode()).hexdigest()},
        'profile_path': str((args.output / 'learned-profile.bin').resolve()),
        'arms': {},
    }
    base = list(cfg['args'])
    save_path = result['profile_path']
    dynamic_args = base + ['--expert-profile-save', save_path,
                           '--expert-profile-save-every', '0']
    dynamic_cfg = dict(cfg)
    dynamic_env = child_env(cfg)
    dynamic_env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                        'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
                        'STRATA_TRACE_ADAPT': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    dynamic_env.pop('STRATA_MTP_BATCH', None)
    dynamic_log = args.output / 'adaptive.log'
    dynamic = StrataEngine(cfg['exe'], dynamic_args, cwd=cfg['cwd'],
                           log=str(dynamic_log), env=dynamic_env)
    adaptive = []
    trace_count = 0
    try:
        for name, prompt in (('short-8192', short_ids), ('long-16384', long_ids),
                             ('short-8192-recovery', short_ids)):
            row, trace_count = run_one(dynamic, dynamic_log, name, prompt, tokenizer,
                                       expected, trace_count)
            adaptive.append(row)
            result['arms']['adaptive'] = adaptive
            (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        dynamic.close()
    if not Path(save_path).is_file():
        raise RuntimeError('adaptive service did not save its learned profile at shutdown')
    save_log = dynamic_log.read_text()
    if 'expert profile saved to' not in save_log:
        raise RuntimeError('saved profile path is absent from the adaptive engine log')
    result['saved_profile_bytes'] = Path(save_path).stat().st_size
    result['saved_profile_sha256'] = hashlib.sha256(Path(save_path).read_bytes()).hexdigest()
    result['adaptive_profile_save_log'] = [line for line in save_log.splitlines()
                                           if 'expert profile saved to' in line]

    # Replay from the exact resident set saved by the adaptive sequence. Remove
    # adaptation controls; keep the remainder of the service configuration fixed.
    static_args = list(base)
    static_args[static_args.index('--expert-profile') + 1] = save_path
    for option in ('--adapt-every', '--adapt-swaps', '--adapt-accepted-only'):
        if option in static_args:
            at = static_args.index(option)
            del static_args[at:at + (1 if option == '--adapt-accepted-only' else 2)]
    static_args.extend(['--adapt-swaps', '0'])
    static_env = child_env(cfg)
    static_env.update({'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                       'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_INTEGRATION_TRACE': '1',
                       'STRATA_PREFILL_CPU_SHARE': '0'})
    static_env.pop('STRATA_MTP_BATCH', None)
    static_log = args.output / 'frozen.log'
    frozen = StrataEngine(cfg['exe'], static_args, cwd=cfg['cwd'],
                          log=str(static_log), env=static_env)
    replay = []
    trace_count = 0
    try:
        for name in ('frozen-profile-short-1', 'frozen-profile-short-2'):
            row, trace_count = run_one(frozen, static_log, name, short_ids, tokenizer,
                                       expected, trace_count)
            replay.append(row)
            result['arms']['frozen_profile'] = replay
            (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        frozen.close()
    frozen_log = static_log.read_text()
    result['frozen_profile_load_log'] = [line for line in frozen_log.splitlines()
                                         if 'profile' in line.lower() and ('loaded' in line.lower() or 'resident' in line.lower())]
    a_first, a_recovery = adaptive[0], adaptive[2]
    f_first, f_second = replay
    result['checks'] = {
        'all_quality_answers_exact': all(row['quality_pass'] for row in adaptive + replay),
        'adaptive_short_answer_equal': a_first['answer'] == a_recovery['answer'],
        'adaptive_short_state_changed': any(a_first['state'][k] != a_recovery['state'][k] for k in STATE_KEYS),
        'frozen_short_answers_equal': f_first['answer'] == f_second['answer'],
        'frozen_short_states_equal': all(f_first['state'][k] == f_second['state'][k] for k in STATE_KEYS),
        'frozen_first_matches_adaptive_recovery_answer': f_first['answer'] == a_recovery['answer'],
        'frozen_first_matches_adaptive_recovery_state': all(f_first['state'][k] == a_recovery['state'][k] for k in STATE_KEYS),
    }
    result['passed'] = (result['checks']['all_quality_answers_exact'] and
                        result['checks']['adaptive_short_answer_equal'] and
                        result['checks']['adaptive_short_state_changed'] and
                        result['checks']['frozen_short_answers_equal'] and
                        result['checks']['frozen_short_states_equal'])
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checks': result['checks'], 'saved_profile_bytes': result['saved_profile_bytes'],
                      'saved_profile_sha256': result['saved_profile_sha256']}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
