"""Compare persistent model state with MTP disabled and enabled; dry-run by default."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from conversation_cache_parity import load_tokenizer, require
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')


def parse_hashes(path):
    found = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if 'STATE_HASH L=' in line:
            fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
            require(set(STATE_KEYS) <= fields.keys(), 'incomplete persistent state fingerprint')
            found.append({key: fields[key] for key in STATE_KEYS})
    return found


def args_for(cfg, spec):
    args = list(cfg['args'])
    for key, value in (('--prompt-cache', '6'), ('--adapt-swaps', '0'), ('--spec', str(max(2, spec))),
                       ('--mtp-max-t', str(spec)), ('--suffix-draft', '0'), ('--spec-min-p', '0')):
        if key in args:
            index = args.index(key)
            args[index + 1] = value
        else:
            args += [key, value]
    return args


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--engine', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True, help='new output directory; existing paths refused')
    ap.add_argument('--tokens', type=int, default=32)
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    if a.tokens < 8:
        ap.error('--tokens must be at least 8 to exercise multiple verifier windows')
    if not a.run:
        print('Dry run: sequential private engines, spec 1 versus spec 4, token and persistent-state parity.')
        return

    cfg = json.loads(a.config.read_text(encoding='utf-8'))
    tok_path = Path(cfg['tokenizer'])
    tok = load_tokenizer(tok_path)
    template_path = tok_path / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    prompt_text = ('Remember these facts for the next turn.\n' +
                   '\n'.join(f'Record {i}: blue square, green triangle, red circle.' for i in range(96)) +
                   '\nReply with a short summary of the colors and shapes.')
    prompt = tok.encode(template.render([{'role': 'user', 'content': prompt_text}], enable_thinking=False),
                        parse_special=True)
    a.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    env = child_env(cfg)
    env['STRATA_STATE_HASH'] = '1'
    env['STRATA_MTP_BATCH'] = '1'
    env['STRATA_PREFILL_CPU_SHARE'] = '0'
    results = {'prompt_sha256': hashlib.sha256(json.dumps(prompt).encode()).hexdigest(),
               'max_new': a.tokens, 'state_fields': STATE_KEYS, 'arms': []}
    for label, spec in (('reference-spec1', 1), ('candidate-spec4', 4)):
        log = a.output / f'{label}.log'
        command = args_for(cfg, spec)
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
        results['arms'].append(arm)
        (a.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')

    reference, candidate = (arm['records'][0] for arm in results['arms'])
    failures = []
    if reference['finish'] not in ('length', 'stop') or candidate['finish'] not in ('length', 'stop'):
        failures.append('request did not finish normally')
    if reference['ids'] != candidate['ids']:
        failures.append('generated token IDs differ')
    if reference['state'] != candidate['state']:
        failures.append('persistent main-model state differs')
    if candidate.get('drafts_offered', 0) <= 0 or candidate.get('drafts_accepted', 0) <= 0:
        failures.append('spec-4 run did not offer and accept MTP drafts')
    if candidate.get('drafts_accepted', 0) > candidate.get('drafts_offered', 0):
        failures.append('accepted MTP count exceeds offered count')
    results['passed'] = True
    results['accepted_prefix_observed'] = {
        'drafts_offered': candidate['drafts_offered'], 'drafts_accepted': candidate['drafts_accepted'],
        'generated_tokens': candidate['generated'], 'persistent_state_equal': True,
    }
    results['comparison'] = {
        'token_ids_equal': reference['ids'] == candidate['ids'],
        'persistent_state_equal': reference['state'] == candidate['state'],
        'differing_state_fields': [key for key in STATE_KEYS if reference['state'].get(key) != candidate['state'].get(key)],
        'reference_length': reference['state']['L'], 'candidate_length': candidate['state']['L'],
        'failures': failures,
    }
    results['accepted_prefix_observed']['persistent_state_equal'] = results['comparison']['persistent_state_equal']
    results['passed'] = not failures
    (a.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    if failures:
        raise AssertionError('; '.join(failures))
    print('PASS: identical token IDs and persistent main-model state; MTP draft counters recorded')
    print(json.dumps(results['accepted_prefix_observed'], sort_keys=True))


if __name__ == '__main__':
    main()
