"""Compare persistent model state with MTP disabled and enabled; dry-run by default."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from conversation_cache_parity import load_tokenizer, require
from prepare_controls import exact_prompt
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env
from pool_worker_screen import read_accepted_prefix_trace

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')


def parse_hashes(path):
    found = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('strata serve: STATE_HASH L='):
            fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
            require(set(STATE_KEYS) <= fields.keys(), 'incomplete persistent state fingerprint')
            found.append({key: fields[key] for key in STATE_KEYS})
    return found


def args_for(cfg, spec, kv_format=None, disable_adaptive_swaps=True):
    args = list(cfg['args'])
    overrides = [('--prompt-cache', '6'), ('--suffix-draft', '0'),
                 ('--spec-min-p', '0')]
    if disable_adaptive_swaps:
        # Accepted-only scheduling is meaningful only while adaptive swaps are
        # active. A static-cache screen must remove both halves of that policy.
        if '--adapt-accepted-only' in args:
            args.remove('--adapt-accepted-only')
        overrides.append(('--adapt-swaps', '0'))
    for key, value in overrides:
        if key in args:
            args[args.index(key) + 1] = value
        else:
            args += [key, value]
    spec_value = max(2, spec)
    if '--spec' in args:
        args[args.index('--spec') + 1] = str(spec_value)
    else:
        args += ['--spec', str(spec_value)]
    if spec <= 0:
        if '--mtp' in args:
            del args[args.index('--mtp'):args.index('--mtp') + 2]
        if '--mtp-max-t' in args:
            del args[args.index('--mtp-max-t'):args.index('--mtp-max-t') + 2]
    else:
        if '--mtp-max-t' in args:
            args[args.index('--mtp-max-t') + 1] = str(spec)
        else:
            args += ['--mtp-max-t', str(spec)]
    if kv_format is not None:
        if '--kv' in args:
            args[args.index('--kv') + 1] = kv_format
        else:
            args += ['--kv', kv_format]
    return args


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--engine', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True, help='new output directory; existing paths refused')
    ap.add_argument('--tokens', type=int, default=32)
    ap.add_argument('--prompt-tokens', type=int, default=512)
    ap.add_argument('--kv-format', choices=('fp16', 'int8', 'q4_0', 'k8v4'), default=None,
                    help='override the configured KV format for every arm')
    ap.add_argument('--windows', type=int, nargs='+', default=[0, 4],
                    help='MTP windows to compare; include 0 for the no-MTP reference')
    ap.add_argument('--use-config-adaptive-swaps', action='store_true',
                    help='preserve the config adaptive-swap policy instead of forcing --adapt-swaps 0')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    if a.tokens < 8:
        ap.error('--tokens must be at least 8 to exercise multiple verifier windows')
    if len(a.windows) < 2 or len(set(a.windows)) != len(a.windows) or a.windows[0] != 0 or any(x < 0 for x in a.windows):
        ap.error('--windows must be unique nonnegative values, start with 0 (MTP off), and contain at least two arms')
    if not a.run:
        print('Dry run: sequential private engines across MTP windows and one KV format; compare tokens and accepted-prefix state.')
        return

    cfg = json.loads(a.config.read_text(encoding='utf-8'))
    tok_path = Path(cfg['tokenizer'])
    tok = load_tokenizer(tok_path)
    template_path = tok_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    def encode(text):
        rendered = template.render([{'role': 'user', 'content': text}], enable_thinking=False)
        return tok.encode(rendered, parse_special=True)
    prompt_text = exact_prompt(a.prompt_tokens, encode)
    prompt = encode(prompt_text)
    a.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    env = child_env(cfg)
    env['STRATA_STATE_HASH'] = '1'
    env['STRATA_ACCEPTED_PREFIX_TRACE'] = '1'
    env['STRATA_INTEGRATION_TRACE'] = '1'
    env['STRATA_MTP_BATCH'] = '1'
    env['STRATA_PREFILL_CPU_SHARE'] = '0'
    base_args = list(cfg['args'])
    configured_kv = base_args[base_args.index('--kv') + 1] if '--kv' in base_args else 'fp16'
    results = {'prompt_sha256': hashlib.sha256(json.dumps(prompt).encode()).hexdigest(),
               'max_new': a.tokens, 'kv_format': a.kv_format or configured_kv,
               'state_fields': STATE_KEYS, 'arms': []}
    for spec in a.windows:
        label = 'mtp-off' if spec == 0 else f'mtp-window{spec}'
        log = a.output / f'{label}.log'
        command = args_for(cfg, spec, a.kv_format,
                           disable_adaptive_swaps=not a.use_config_adaptive_swaps)
        engine = StrataEngine(str(a.engine.resolve()), command, cwd=cfg.get('cwd'), log=str(log), env=env)
        arm = {'name': label, 'spec': spec, 'args': command, 'info': dict(engine.info), 'records': []}
        with a.engine.open('rb') as binary:
            arm['engine_sha256'] = hashlib.file_digest(binary, 'sha256').hexdigest()
        try:
            ids = [token for token in engine.generate(prompt, a.tokens, {'temperature': 0}, threading.Event())
                   if token is not None]
            arm['records'].append({'ids': ids, 'text': tok.decode(ids), **engine.last})
        finally:
            engine.close()
        hashes = parse_hashes(log)
        require(len(hashes) == 1, f'{label}: expected one completed-request fingerprint')
        arm['records'][0]['state'] = hashes[0]
        arm['records'][0]['accepted_prefix_trace'] = read_accepted_prefix_trace(log)
        require(bool(arm['records'][0]['accepted_prefix_trace']), f'{label}: accepted-prefix trace missing')
        trace_ids = [token for entry in arm['records'][0]['accepted_prefix_trace'] for token in entry['token_ids']]
        require(trace_ids == ids, f'{label}: accepted-prefix tokens do not match published output')
        results['arms'].append(arm)
        (a.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')

    reference = results['arms'][0]['records'][0]
    comparisons = []
    for arm in results['arms'][1:]:
        candidate = arm['records'][0]
        failures = []
        if reference['finish'] not in ('length', 'stop') or candidate['finish'] not in ('length', 'stop'):
            failures.append('request did not finish normally')
        if reference['ids'] != candidate['ids']:
            failures.append('generated token IDs differ')
        differing_final = [key for key in STATE_KEYS if reference['state'].get(key) != candidate['state'].get(key)]
        if differing_final:
            failures.append('final persistent main-model state differs: ' + ', '.join(differing_final))
        if candidate.get('drafts_offered', 0) <= 0 or candidate.get('drafts_accepted', 0) <= 0:
            failures.append('MTP run did not offer and accept drafts')
        if candidate.get('drafts_accepted', 0) > candidate.get('drafts_offered', 0):
            failures.append('accepted MTP count exceeds offered count')
        reference_by_prefix = {}
        prefix_count = 0
        for entry in reference['accepted_prefix_trace']:
            prefix_count += entry['committed']
            reference_by_prefix[prefix_count] = entry['state']
        prefix_checks = []
        prefix_count = 0
        for entry in candidate['accepted_prefix_trace']:
            prefix_count += entry['committed']
            prior = reference_by_prefix.get(prefix_count)
            if prior is not None:
                differing = [key for key in STATE_KEYS if prior.get(key) != entry['state'].get(key)]
                prefix_checks.append({'generated_prefix_tokens': prefix_count, 'equal': not differing,
                                     'differing_state_fields': differing})
                if differing:
                    failures.append(f'persistent state differs at committed prefix {prefix_count}: ' + ', '.join(differing))
        if not prefix_checks:
            failures.append('no shared accepted-prefix boundary between reference and MTP run')
        comparisons.append({
            'candidate': arm['name'], 'token_ids_equal': reference['ids'] == candidate['ids'],
            'final_state_equal': not differing_final, 'final_state_differing_fields': differing_final,
            'drafts_offered': candidate.get('drafts_offered', 0),
            'drafts_accepted': candidate.get('drafts_accepted', 0),
            'matched_commit_boundaries': prefix_checks, 'failures': failures,
        })
    results['comparisons'] = comparisons
    results['passed'] = not any(row['failures'] for row in comparisons)
    (a.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'passed': results['passed'], 'comparisons': comparisons}, sort_keys=True))
    if not results['passed']:
        raise AssertionError('; '.join(f"{row['candidate']}: {'; '.join(row['failures'])}" for row in comparisons if row['failures']))
    print('PASS: identical token IDs and persistent main-model state at compared accepted prefixes; MTP draft counters recorded')


if __name__ == '__main__':
    main()
