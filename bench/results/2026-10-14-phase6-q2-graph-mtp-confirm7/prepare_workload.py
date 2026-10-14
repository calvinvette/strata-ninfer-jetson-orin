#!/usr/bin/env python3
"""Prepare one exact held-out Q2_0 API prompt without starting a service."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import load_tokenizer
from prepare_controls import exact_prompt_variant
from serve.frontend import ChatTemplate


HERE = Path(__file__).resolve().parent
TOKENIZER = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')


def main():
    tokenizer = load_tokenizer(TOKENIZER)
    template = ChatTemplate(TOKENIZER / 'chat_template.jinja')

    def encode(text):
        rendered = template.render([{'role': 'user', 'content': text}], enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    text = exact_prompt_variant(512, encode, 'heldout_blue')
    ids = encode(text)
    if len(ids) != 512:
        raise RuntimeError(f'expected 512 formatted tokens, got {len(ids)}')
    token_path = HERE / 'heldout-512.tokens'
    token_path.write_text(','.join(map(str, ids)) + '\n')
    workload = {
        'workloads': [{
            'cell': 'heldout-blue-pp512-tg64',
            'prompt_tokens': 512,
            'generate_tokens': 64,
            'tokens_file': str(token_path.resolve()),
            'tokens_sha256': hashlib.sha256(token_path.read_bytes()).hexdigest(),
            'messages': [{'role': 'user', 'content': text}],
            'chat_template_kwargs': {'enable_thinking': False},
        }],
        'tokenizer': str(TOKENIZER),
        'prompt_policy': 'heldout_blue 512 tokens after the model chat template; 64 output tokens',
    }
    (HERE / 'workloads.json').write_text(json.dumps(workload, indent=2) + '\n')
    print(json.dumps({'prompt_tokens': len(ids), 'tokens_sha256': workload['workloads'][0]['tokens_sha256'],
                      'prompt_sha256': hashlib.sha256(text.encode()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
