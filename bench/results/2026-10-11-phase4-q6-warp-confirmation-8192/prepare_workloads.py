#!/usr/bin/env python3
"""Build exact-length, distinct Q6_K confirmation and warmup API workloads."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from strata_tokenizer import Tokenizer
from serve.frontend import ChatTemplate

TOKENIZER = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
OUTPUT = Path(__file__).resolve().parent
vocab = json.loads((TOKENIZER / 'vocab.json').read_text())
tokens = [None] * len(vocab)
for text, index in vocab.items():
    tokens[index] = text
tok = Tokenizer(tokens, (TOKENIZER / 'merges.txt').read_text().split('\n'),
                json.loads((TOKENIZER / 'token_type.json').read_text()))
template = ChatTemplate(TOKENIZER / 'chat_template.jinja')


def encode(content):
    rendered = template.render([{'role': 'user', 'content': content}], enable_thinking=False)
    return tok.encode(rendered, parse_special=True)


def exact(target, prefix, filler, suffix):
    low, high = 0, target
    while low <= high:
        count = (low + high) // 2
        content = prefix + filler * count + suffix
        actual = len(encode(content))
        if actual == target:
            return content, encode(content)
        if actual < target:
            low = count + 1
        else:
            high = count - 1
    raise RuntimeError(f'cannot construct exact {target}-token prompt')


measured, measured_ids = exact(
    512, 'Field report: ', 'station ',
    '\nThe rain gauge recorded a short shower before the creek-depth sensor rose. '
    'By evening the level began to fall while the air cooled. There is no second gauge '
    'and the notebook does not record upstream releases. Using only these observations, '
    'explain what sequence was observed, why it does not prove rain caused the rise, '
    'identify a plausible confounder, and propose one useful follow-up measurement. '
    'Write at least 250 words and distinguish facts from inference.')
warmup, warmup_ids = exact(
    172, 'Warm-up field note: ', 'blue ',
    '\nExplain how a technician should record a measurement, check the instrument, '
    'and separate an observation from an assumption. Write at least 250 words.')


def write_workload(name, cell, prompt, ids, generated):
    token_path = OUTPUT / f'{name}.tokens'
    token_path.write_text(','.join(map(str, ids)) + '\n')
    row = {'cell': cell, 'prompt_tokens': len(ids), 'generate_tokens': generated,
           'tokens_file': str(token_path.resolve()),
           'tokens_sha256': hashlib.sha256(token_path.read_bytes()).hexdigest(),
           'messages': [{'role': 'user', 'content': prompt}],
           'chat_template_kwargs': {'enable_thinking': False}}
    return {'workloads': [row], 'tokenizer': [
        {'path': str((TOKENIZER / f).resolve()),
         'sha256': hashlib.sha256((TOKENIZER / f).read_bytes()).hexdigest()}
        for f in ('vocab.json', 'merges.txt', 'token_type.json', 'chat_template.jinja')],
        'policy': 'exact formatted input verified with Strata tokenizer and chat template; API usage rechecked per cell'}


(OUTPUT / 'workloads.json').write_text(json.dumps(
    write_workload('measured', 'heldout-512-context8192', measured, measured_ids, 64), indent=2) + '\n')
(OUTPUT / 'warmup-workloads.json').write_text(json.dumps(
    write_workload('warmup', 'distinct-warmup-172', warmup, warmup_ids, 64), indent=2) + '\n')
print(json.dumps({'measured_prompt_tokens': len(measured_ids),
                  'warmup_prompt_tokens': len(warmup_ids),
                  'measured_sha256': hashlib.sha256((OUTPUT / 'measured.tokens').read_bytes()).hexdigest(),
                  'warmup_sha256': hashlib.sha256((OUTPUT / 'warmup.tokens').read_bytes()).hexdigest()}, indent=2))
