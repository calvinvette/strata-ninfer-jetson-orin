#!/usr/bin/env python3
"""Run one exact-answer retrieval/scoring task under strict NInfer, MTP off/4."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import STATE_KEYS, args_for, parse_hashes
from conversation_cache_parity import load_tokenizer, require
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--engine', type=Path, required=True)
    ap.add_argument('--workload', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--compare-strata-control', action='store_true',
                    help='compare MTP-off Strata backend against MTP-off strict NInfer')
    ap.add_argument('--compare-cpu-miss-staged', action='store_true',
                    help='compare MTP-off CPU miss fallback against strict NInfer staging')
    ap.add_argument('--compare-staged-backends', action='store_true',
                    help='compare Strata and strict NInfer compute with staging enabled in both arms')
    ap.add_argument('--dump-gdn', action='store_true',
                    help='write final accepted-prefix GDN arrays for numeric comparison')
    ap.add_argument('--dump-gdn-at', type=int,
                    help='exact committed length for the one-shot GDN dump (defaults to max generation length)')
    ap.add_argument('--max-new', type=int,
                    help='override fixture generation allowance for prefix diagnostics')
    ap.add_argument('--capture-moe-layer', type=int,
                    help='capture route, input, per-expert parts and output for one verifier layer')
    ap.add_argument('--capture-moe-position', type=int,
                    help='filter the MoE capture to one token position')
    ap.add_argument('--capture-moe-positions', type=int, nargs='+',
                    help='filter the MoE capture to several increasing token positions')
    ap.add_argument('--capture-gdn-layer', type=int,
                    help='capture GDN and feed-forward intermediates for one verifier layer')
    ap.add_argument('--capture-gdn-position', type=int,
                    help='filter the GDN capture to one token position')
    ap.add_argument('--capture-gdn-positions', type=int, nargs='+',
                    help='filter the GDN capture to several increasing token positions')
    ap.add_argument('--capture-gdn-commit-layer', type=int,
                    help='capture committed GDN state at one GDN layer')
    ap.add_argument('--capture-gdn-commit-positions', type=int, nargs='+',
                    help='filter committed GDN state to several increasing token positions')
    ap.add_argument('--cpu-q8-1-selector',
                    help='opt in to a CPU Q8_1 dot selector for the CPU-miss arm only')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    comparison_modes = (a.compare_strata_control, a.compare_cpu_miss_staged, a.compare_staged_backends)
    if sum(comparison_modes) > 1:
        ap.error('choose only one comparison mode')
    if a.capture_moe_position is not None and a.capture_moe_positions is not None:
        ap.error('use only one of --capture-moe-position and --capture-moe-positions')
    if a.capture_moe_positions is not None and (
            not a.capture_moe_positions or any(x < 0 for x in a.capture_moe_positions) or
            a.capture_moe_positions != sorted(set(a.capture_moe_positions))):
        ap.error('--capture-moe-positions must be unique, increasing, nonnegative integers')
    if a.capture_gdn_position is not None and a.capture_gdn_positions is not None:
        ap.error('use only one of --capture-gdn-position and --capture-gdn-positions')
    if a.capture_gdn_positions is not None and (
            not a.capture_gdn_positions or any(x < 0 for x in a.capture_gdn_positions) or
            a.capture_gdn_positions != sorted(set(a.capture_gdn_positions))):
        ap.error('--capture-gdn-positions must be unique, increasing, nonnegative integers')
    if (a.capture_gdn_commit_layer is None) != (a.capture_gdn_commit_positions is None):
        ap.error('--capture-gdn-commit-layer and --capture-gdn-commit-positions must be used together')
    if a.capture_gdn_commit_layer is not None and not 0 <= a.capture_gdn_commit_layer < 48:
        ap.error('--capture-gdn-commit-layer must be in [0, 47]')
    if a.capture_gdn_commit_positions is not None and (
            not a.capture_gdn_commit_positions or any(x < 0 for x in a.capture_gdn_commit_positions) or
            a.capture_gdn_commit_positions != sorted(set(a.capture_gdn_commit_positions))):
        ap.error('--capture-gdn-commit-positions must be unique, increasing, nonnegative integers')
    if a.capture_gdn_position is not None and a.capture_gdn_layer is None:
        ap.error('--capture-gdn-position requires --capture-gdn-layer')
    if a.capture_gdn_layer is not None and not 0 <= a.capture_gdn_layer < 48:
        ap.error('--capture-gdn-layer must be in [0, 47]')
    if a.capture_gdn_position is not None and a.capture_gdn_position < 0:
        ap.error('--capture-gdn-position must be nonnegative')
    if a.cpu_q8_1_selector is not None and not a.compare_cpu_miss_staged:
        ap.error('--cpu-q8-1-selector requires --compare-cpu-miss-staged')
    cfg = json.loads(a.config.read_text())
    workload = json.loads(a.workload.read_text())['workloads'][0]
    max_new = a.max_new if a.max_new is not None else workload['generate_tokens']
    if max_new < 1:
        ap.error('--max-new must be positive')
    expected = workload.get('expected_text')
    if expected is None and 'expected_codes' in workload and 'expected_suffix_sum' in workload:
        expected = (f"EARLY={workload['expected_codes'][0]}, "
                    f"MIDDLE={workload['expected_codes'][1]}, "
                    f"LATE={workload['expected_codes'][2]}, "
                    f"SUM={workload['expected_suffix_sum']}")
    tokenizer_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tokenizer_path)
    template_path = tokenizer_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    prompt_text = workload['messages'][0]['content']
    prompt = tokenizer.encode(template.render(workload['messages'], enable_thinking=False), parse_special=True)
    if len(prompt) != workload['prompt_tokens']:
        raise ValueError(f"fixture says {workload['prompt_tokens']} tokens; formatted prompt has {len(prompt)}")
    if a.output.exists():
        raise ValueError(f'output already exists: {a.output}')
    if not a.run:
        print(json.dumps({'prompt_tokens': len(prompt), 'prompt_sha256': hashlib.sha256(
            json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(), 'max_new': max_new,
            'expected': expected}, indent=2))
        return 0

    a.output.mkdir(parents=True)
    env = child_env(cfg)
    env.update({'STRATA_STATE_HASH': '1', 'STRATA_INTEGRATION_TRACE': '1',
                'STRATA_MTP_BATCH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    result = {'workload': workload['cell'], 'prompt_tokens': len(prompt),
              'prompt_content_sha256': hashlib.sha256(prompt_text.encode()).hexdigest(),
              'prompt_ids_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
              'expected': expected, 'max_new': max_new, 'state_fields': STATE_KEYS, 'arms': [], 'failures': []}
    if a.compare_strata_control:
        arms = (('strata-control', 'strata', 0), ('ninfer-control', 'ninfer', 0))
    elif a.compare_cpu_miss_staged:
        arms = (('cpu-miss', 'strata', 0), ('ninfer-staged', 'ninfer', 0))
    elif a.compare_staged_backends:
        arms = (('strata-staged', 'strata', 0), ('ninfer-staged', 'ninfer', 0))
    else:
        arms = (('mtp-off', 'ninfer', 0), ('mtp4', 'ninfer', 4))
    for name, backend, window in arms:
        log = a.output / f'{name}.log'
        command = args_for(cfg, window, disable_adaptive_swaps=True)
        if backend == 'strata':
            if '--expert-backend' in command:
                command[command.index('--expert-backend') + 1] = 'strata'
            if '--expert-backend-strict' in command:
                command.remove('--expert-backend-strict')
        if (a.compare_cpu_miss_staged or a.compare_staged_backends) and '--pcie-frac' in command:
            command[command.index('--pcie-frac') + 1] = (
                '0.0' if a.compare_cpu_miss_staged and backend == 'strata' else '1.0')
        arm_env = dict(env)
        if a.cpu_q8_1_selector is not None and name == 'cpu-miss':
            arm_env['STRATA_NATIVE_CPU_Q8_1_DOT'] = a.cpu_q8_1_selector
        arm_env['STRATA_RESIDENCY_DUMP'] = str((a.output / f'{name}.residency.csv').resolve())
        if a.dump_gdn:
            arm_env['STRATA_STATE_DUMP_GDN'] = str((a.output / f'{name}.gdn.bin').resolve())
            dump_at = a.dump_gdn_at if a.dump_gdn_at is not None else len(prompt) + max_new - 1
            arm_env['STRATA_STATE_DUMP_GDN_AT'] = str(dump_at)
        if a.capture_moe_layer is not None:
            for kind in ('ROUTE', 'INPUT', 'PARTS', 'OUTPUT'):
                stem = f'STRATA_VERIFY_DUMP_MOE_{kind}'
                arm_env[f'{stem}_LAYER'] = str(a.capture_moe_layer)
                arm_env[f'{stem}_PATH'] = str((a.output / f'{name}.layer{a.capture_moe_layer}.{kind.lower()}').resolve())
                if kind in ('ROUTE', 'PARTS', 'OUTPUT'):
                    arm_env[f'{stem}_BATCH'] = '1'
                if a.capture_moe_positions is not None:
                    arm_env[f'{stem}_POSITIONS'] = ','.join(map(str, a.capture_moe_positions))
                elif a.capture_moe_position is not None:
                    arm_env[f'{stem}_POSITION'] = str(a.capture_moe_position)
        if a.capture_gdn_layer is not None:
            arm_env['STRATA_VERIFY_DUMP_GDN_LAYER'] = str(a.capture_gdn_layer)
            arm_env['STRATA_VERIFY_DUMP_GDN_PATH'] = str(
                (a.output / f'{name}.layer{a.capture_gdn_layer}.gdn-diag').resolve())
            if a.capture_gdn_positions is not None:
                arm_env['STRATA_VERIFY_DUMP_GDN_POSITIONS'] = ','.join(map(str, a.capture_gdn_positions))
            elif a.capture_gdn_position is not None:
                arm_env['STRATA_VERIFY_DUMP_GDN_POSITION'] = str(a.capture_gdn_position)
        if a.capture_gdn_commit_layer is not None:
            arm_env['STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER'] = str(a.capture_gdn_commit_layer)
            arm_env['STRATA_VERIFY_DUMP_GDN_COMMIT_PATH'] = str(
                (a.output / f'{name}.gdn-commit').resolve())
            arm_env['STRATA_VERIFY_DUMP_GDN_COMMIT_POSITIONS'] = ','.join(
                map(str, a.capture_gdn_commit_positions))
        engine = StrataEngine(str(a.engine.resolve()), command, cwd=cfg.get('cwd'),
                              log=str(log), env=arm_env)
        try:
            ids = [token for token in engine.generate(prompt, max_new,
                    {'temperature': 0}, threading.Event()) if token is not None]
            # The engine intentionally yields its terminal chat token; compare
            # the user-visible answer after removing that protocol marker.
            text = tokenizer.decode(ids).replace('<|im_end|>', '').strip()
            states = parse_hashes(log)
            require(len(states) == 1, f'{name}: expected one final state fingerprint')
            arm = {'name': name, 'window': window, 'args': command, 'ids': ids,
                   'text': text, 'state': states[0], 'usage': dict(engine.last),
                   'residency_sha256': hashlib.sha256(
                       (a.output / f'{name}.residency.csv').read_bytes()).hexdigest()
                       if (a.output / f'{name}.residency.csv').exists() else None}
            result['arms'].append(arm)
            if expected is not None and max_new == workload['generate_tokens'] and text != expected:
                result['failures'].append(f'{name}: exact answer mismatch: {text!r}')
        except Exception as exc:
            result['failures'].append(f'{name}: {type(exc).__name__}: {exc}')
        finally:
            engine.close()
    if len(result['arms']) == 2:
        off, mtp = result['arms']
        result['token_ids_equal'] = off['ids'] == mtp['ids']
        result['final_state_equal'] = all(off['state'].get(k) == mtp['state'].get(k) for k in STATE_KEYS)
        result['residency_equal'] = (off.get('residency_sha256') is not None and
                                     off.get('residency_sha256') == mtp.get('residency_sha256'))
        result['state_differing_fields'] = [k for k in STATE_KEYS if off['state'].get(k) != mtp['state'].get(k)]
        if not result['token_ids_equal']:
            result['failures'].append(f"{off['name']} and {mtp['name']} token IDs differ")
        if not result['final_state_equal']:
            result['failures'].append(f"{off['name']} and {mtp['name']} final state differ")
        if (a.compare_cpu_miss_staged or a.compare_staged_backends) and not result['residency_equal']:
            result['failures'].append(f"{off['name']} and {mtp['name']} resident maps differ or were not captured")
    result['exact_answer_check'] = expected is not None and max_new == workload['generate_tokens']
    result['passed'] = not result['failures'] and len(result['arms']) == 2
    (a.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result.get(k) for k in ('passed', 'failures', 'token_ids_equal',
                   'final_state_equal', 'state_differing_fields')}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
