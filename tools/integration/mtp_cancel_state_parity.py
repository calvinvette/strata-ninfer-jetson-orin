"""Compare canceled MTP state with a fresh request at the exact committed prefix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from benchmark_control import request as get_json
from run_control import write_result

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full',
              'kv', 'mtp', 'stale', 'ple_prev')
PREFIX_RE = re.compile(
    r'ACCEPTED_PREFIX position=(\d+) window=(\d+) accepted_drafts=(\d+) '
    r'committed=(\d+) tokens=([0-9,]+) state=\{STATE_HASH (.+)\}')


def parse_prefix_entries(lines):
    entries = []
    for line in lines:
        if 'ACCEPTED_PREFIX ' not in line:
            continue
        match = PREFIX_RE.search(line)
        if not match:
            raise ValueError(f'malformed accepted-prefix trace: {line.strip()}')
        position, window, accepted, committed = map(int, match.group(1, 2, 3, 4))
        token_ids = [int(value) for value in match.group(5).split(',')]
        state = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', match.group(6)))
        if committed != len(token_ids) or committed < 1 or not set(STATE_KEYS) <= state.keys():
            raise ValueError(f'incomplete accepted-prefix record: {line.strip()}')
        entries.append({'position': position, 'window': window,
                        'accepted_drafts': accepted, 'committed': committed,
                        'token_ids': token_ids,
                        'state': {key: state[key] for key in STATE_KEYS}})
    return entries


def compare_prefix_traces(cancelled, reference):
    cancelled_ids = [token for row in cancelled for token in row['token_ids']]
    reference_ids = [token for row in reference for token in row['token_ids']]
    failures = []
    if cancelled_ids != reference_ids:
        failures.append('committed token IDs differ')
    by_length = {row['state']['L']: row for row in reference}
    shared = []
    for row in cancelled:
        length = row['state']['L']
        other = by_length.get(length)
        if other is None:
            failures.append(f'reference lacks accepted-prefix state at L={length}')
        elif row['state'] != other['state']:
            failures.append(f'persistent state differs at accepted prefix L={length}')
        else:
            shared.append(length)
    if not cancelled or not reference:
        failures.append('accepted-prefix trace is empty')
    elif cancelled[-1]['state']['L'] != reference[-1]['state']['L']:
        failures.append('final committed prefix lengths differ')
    return {'passed': not failures, 'failures': failures,
            'cancelled_token_ids': cancelled_ids,
            'reference_token_ids': reference_ids,
            'shared_state_lengths': shared,
            'cancelled_final_state': cancelled[-1]['state'] if cancelled else None,
            'reference_final_state': reference[-1]['state'] if reference else None}


def start_server(cfg, config_path, server_env):
    process = subprocess.Popen(
        [sys.executable, '-m', 'serve.server', '--engine', 'strata',
         '--config', str(config_path.resolve()), '--host', '127.0.0.1',
         '--port', str(cfg['port'])], cwd=cfg['cwd'], env=server_env)
    base = f"http://127.0.0.1:{cfg['port']}"
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server on {cfg['port']} exited early: {process.returncode}")
        try:
            health = get_json(base, '/health', timeout=5)
            if health.get('model'):
                return process, base, health
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(0.5)
    process.terminate()
    raise TimeoutError(f"server on {cfg['port']} did not become ready")


def stop_server(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def state_dump_env(env, output_path, accepted_length):
    """Enable a one-shot GDN dump at an exact accepted-prefix length."""
    result = dict(env)
    if accepted_length is not None:
        result['STRATA_STATE_DUMP_GDN'] = str(Path(output_path).resolve())
        result['STRATA_STATE_DUMP_GDN_AT'] = str(accepted_length)
    return result


def config_with_engine_env(config, env):
    """Make the server config's engine overrides agree with the server process env."""
    result = dict(config)
    result['env'] = dict(env)
    return result


def config_with_expert_cache(config, slots):
    """Copy a server config with one fixed expert-cache capacity."""
    result = dict(config)
    engine_args = list(config.get('args', []))
    if '--expert-cache' in engine_args:
        engine_args[engine_args.index('--expert-cache') + 1] = str(slots)
    else:
        engine_args.extend(['--expert-cache', str(slots)])
    result['args'] = engine_args
    return result


def reset_stream(response):
    """Close the read side; the server's EOF watcher then sends STOP to the engine."""
    response.close()


def wait_for_cancel_log(path, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            lines = path.read_text(errors='replace').splitlines()
            for index, line in enumerate(lines):
                if 'strata serve: prompt ' in line:
                    return lines, index
        time.sleep(0.1)
    raise TimeoutError('engine did not record a canceled request')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True,
                        help='base config with the MTP weights path enabled')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cancel-chunks', type=int, default=8,
                        help='close the stream after this many non-empty text deltas')
    parser.add_argument('--reference-repeats', type=int, default=3,
                        help='fresh exact-length reference processes used to distinguish cancellation drift from run variation')
    parser.add_argument('--dump-gdn-at', type=int,
                        help='optionally dump float32 GDN state at this exact accepted length in each process')
    parser.add_argument('--fixed-expert-cache', type=int,
                        help='override every process with the same positive expert-cache slot count')
    parser.add_argument('--prompt-text', default=(
        'Write the integers from 1 through 1000 separated by single spaces. '
        'Do not add an introduction or conclusion, and do not stop before 1000.'))
    args = parser.parse_args()
    if (args.output.exists() or args.cancel_chunks < 1 or args.reference_repeats < 1
            or (args.fixed_expert_cache is not None and args.fixed_expert_cache < 1)):
        parser.error('output must be new; cancel-chunks, reference-repeats and fixed expert-cache must be positive')
    cfg = json.loads(args.config.read_text())
    if '--mtp' not in cfg.get('args', []):
        parser.error('source config has no --mtp weights path')
    mtp_path = Path(cfg['args'][cfg['args'].index('--mtp') + 1])
    if not mtp_path.exists():
        parser.error(f'MTP weights do not exist: {mtp_path}')
    args.output.mkdir(parents=True)
    if args.fixed_expert_cache is not None:
        cfg = config_with_expert_cache(cfg, args.fixed_expert_cache)
    result = {'schema': 1, 'scope': 'MTP accepted-prefix cancellation state parity and same-process recovery',
              'model': cfg.get('model_name'), 'workload_cell': 'open-ended-integer-list',
              'prompt_text': args.prompt_text, 'requested_output_tokens': 1024,
              'cancel_after_nonempty_deltas': args.cancel_chunks,
              'reference_repeats': args.reference_repeats,
              'fixed_expert_cache_slots': args.fixed_expert_cache,
              'dump_gdn_at': args.dump_gdn_at,
              'effective_engine_env': {
                  key: base_value for key, base_value in {
                      'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_MTP_BATCH': '1',
                      'STRATA_STATE_HASH': '1', 'STRATA_STATE_HASH_GDN': '1',
                      'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                  }.items()},
              'checks': []}
    result_path = args.output / 'result.json'
    write_result(result_path, result)
    base_env = dict(cfg.get('env', {}))
    base_env.update({'STRATA_STATE_HASH': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1',
                     'STRATA_INTEGRATION_TRACE': '1', 'STRATA_MTP_BATCH': '1',
                     'STRATA_STATE_HASH_GDN': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
    body_base = {'messages': [{'role': 'user', 'content': args.prompt_text}],
                 'chat_template_kwargs': {'enable_thinking': False},
                 'temperature': 0, 'strata_tune': {'ignore_eos': True}}
    cancel_env = state_dump_env(base_env, args.output / 'gdn-cancel.bin', args.dump_gdn_at)
    cancel_cfg = config_with_engine_env(cfg, cancel_env)
    cancel_cfg.update(port=int(cfg['port']) + 20,
                      log=str((args.output / 'engine-cancel.log').resolve()))
    cancel_config_path = args.output / 'server-config-cancel.json'
    cancel_config_path.write_text(json.dumps(cancel_cfg, indent=2) + '\n')
    cancel_row = {'check': 'stream_cancel', 'status': 'started'}
    result['checks'].append(cancel_row)
    write_result(result_path, result)
    cancel_server = None
    try:
        cancel_server, cancel_base, cancel_health = start_server(cancel_cfg, cancel_config_path, cancel_env)
        cancel_body = dict(body_base, model=cancel_health['model'], max_tokens=1024, stream=True)
        stream_request = urllib.request.Request(
            cancel_base + '/v1/chat/completions',
            data=json.dumps(cancel_body).encode(),
            headers={'Content-Type': 'application/json'})
        response = urllib.request.urlopen(stream_request, timeout=300)
        visible = ''
        chunks = 0
        ended_normally = False
        for raw_line in response:
            line = raw_line.decode('utf-8', errors='replace').strip()
            if line == 'data: [DONE]':
                ended_normally = True
                break
            if not line or not line.startswith('data: '):
                continue
            event = json.loads(line[6:])
            if event.get('choices'):
                text = event['choices'][0].get('delta', {}).get('content') or ''
                if text:
                    visible += text
                    chunks += 1
                    if chunks >= args.cancel_chunks:
                        break
        reset_stream(response)
        if ended_normally or chunks < args.cancel_chunks:
            raise RuntimeError(f'stream ended naturally after {chunks} non-empty deltas before cancellation')
        lines, summary_index = wait_for_cancel_log(Path(cancel_cfg['log']))
        if '(cancelled)' not in lines[summary_index]:
            raise RuntimeError('engine completed the request before client cancellation was observed')
        cancel_trace = parse_prefix_entries(lines[:summary_index])
        committed = sum(len(row['token_ids']) for row in cancel_trace)
        if committed < 1:
            raise ValueError('canceled request committed no accepted-prefix tokens')
        cancel_row.update(status='pass', visible_text=visible, visible_deltas=chunks,
                          committed_tokens=committed,
                          accepted_prefix_trace=cancel_trace,
                          prompt_summary=lines[summary_index])
        result['canceled_token_count'] = committed
        write_result(result_path, result)
        recovery = {'check': 'same_process_recovery', 'status': 'started'}
        result['checks'].append(recovery)
        recovery_body = {'model': cancel_health['model'],
                         'messages': [{'role': 'user', 'content': 'Reply with exactly: Hello Orin!'}],
                         'chat_template_kwargs': {'enable_thinking': False},
                         'temperature': 0, 'max_tokens': 24}
        recovered = get_json(cancel_base, '/v1/chat/completions', timeout=180, body=recovery_body)
        recovered_text = recovered['choices'][0]['message'].get('content', '').strip()
        recovery.update(status='pass' if recovered_text == 'Hello Orin!' else 'fail',
                        response_text=recovered_text,
                        reason='expected recovery response' if recovered_text == 'Hello Orin!' else 'unexpected recovery text')
        recovery['server_alive'] = cancel_server.poll() is None
        if not recovery['server_alive']:
            recovery.update(status='fail', reason=f'server exited: {cancel_server.returncode}')
        write_result(result_path, result)
    except Exception as exc:
        cancel_row.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
        result['error'] = cancel_row['reason']
        write_result(result_path, result)
        return 1
    finally:
        if cancel_server is not None:
            stop_server(cancel_server)

    reference = {'check': 'fresh_exact_length_references', 'status': 'started',
                 'runs': [], 'comparisons': []}
    result['checks'].append(reference)
    write_result(result_path, result)
    reference_traces = []
    reference_texts = []
    try:
        for repeat in range(args.reference_repeats):
            reference_env = state_dump_env(base_env, args.output / f'gdn-reference-{repeat:02d}.bin',
                                           args.dump_gdn_at)
            reference_cfg = config_with_engine_env(cfg, reference_env)
            reference_cfg.update(
                port=int(cfg['port']) + 21 + repeat,
                log=str((args.output / f'engine-reference-{repeat:02d}.log').resolve()))
            reference_config_path = args.output / f'server-config-reference-{repeat:02d}.json'
            reference_config_path.write_text(json.dumps(reference_cfg, indent=2) + '\n')
            reference_server = None
            try:
                reference_server, reference_base, reference_health = start_server(
                    reference_cfg, reference_config_path, reference_env)
                reference_body = dict(body_base, model=reference_health['model'],
                                      max_tokens=result['canceled_token_count'], stream=False)
                response = get_json(reference_base, '/v1/chat/completions', timeout=300,
                                    body=reference_body)
                reference_text = response['choices'][0]['message'].get('content', '')
                lines = Path(reference_cfg['log']).read_text(errors='replace').splitlines()
                ref_trace = parse_prefix_entries(lines)
                cancel_comparison = compare_prefix_traces(cancel_trace, ref_trace)
                visible_prefix = reference_text.startswith(cancel_row['visible_text'])
                if not visible_prefix:
                    cancel_comparison['failures'].append(
                        'visible canceled text is not a prefix of the exact-length reference')
                    cancel_comparison['passed'] = False
                repeat_row = {
                    'repeat': repeat, 'status': 'pass' if cancel_comparison['passed'] else 'fail',
                    'completion_tokens': response.get('usage', {}).get('completion_tokens'),
                    'reference_text': reference_text,
                    'cancel_visible_text_is_reference_prefix': visible_prefix,
                    'reference_trace': ref_trace,
                    'cancellation_comparison': cancel_comparison,
                }
                if reference_traces:
                    baseline_comparison = compare_prefix_traces(reference_traces[0], ref_trace)
                    repeat_row['reference_repeatability'] = baseline_comparison
                    reference['comparisons'].append({
                        'repeat': repeat,
                        'matches_first_reference': baseline_comparison['passed'],
                        'comparison': baseline_comparison,
                    })
                else:
                    reference['comparisons'].append({
                        'repeat': repeat, 'matches_first_reference': True,
                        'comparison': None,
                    })
                reference_traces.append(ref_trace)
                reference_texts.append(reference_text)
                reference['runs'].append(repeat_row)
                reference['status'] = 'running'
                write_result(result_path, result)
            finally:
                if reference_server is not None:
                    stop_server(reference_server)
        all_cancel_match = all(row['cancellation_comparison']['passed']
                               for row in reference['runs'])
        references_repeat = all(row['matches_first_reference']
                                for row in reference['comparisons'])
        texts_repeat = len(set(reference_texts)) == 1
        reference['references_repeatable'] = references_repeat and texts_repeat
        reference['status'] = 'pass' if all_cancel_match and references_repeat and texts_repeat else 'fail'
        reference['reason'] = ('all references match canceled committed state and each other'
                               if reference['status'] == 'pass' else
                               'cancellation parity or exact-length reference repeatability failed')
        write_result(result_path, result)
        return int(reference['status'] != 'pass' or
                   any(row.get('status') != 'pass' for row in result['checks']))
    except Exception as exc:
        reference.update(status='fail', reason=f'{type(exc).__name__}: {exc}')
        result['error'] = reference['reason']
        write_result(result_path, result)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
