#!/usr/bin/env python3
"""Tokenize the checked-in semantic task with the local Q2_0 tokenizer."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from accepted_prefix_parity import load_tokenizer
from serve.frontend import ChatTemplate
HERE = Path(__file__).resolve().parent
TOKENIZER = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')

def main():
    tok = load_tokenizer(TOKENIZER)
    template = ChatTemplate(TOKENIZER / 'chat_template.jinja')
    prompt = (HERE / 'prompt.txt').read_text().rstrip('\n')
    rendered = template.render([{'role': 'user', 'content': prompt}], enable_thinking=False)
    ids = tok.encode(rendered, parse_special=True)
    if len(ids) != 512:
        raise SystemExit(f'expected exactly 512 formatted tokens, found {len(ids)}')
    token_file = HERE / 'prompt.tokens'
    token_file.write_text(','.join(map(str, ids)) + '\n')
    digest = hashlib.sha256(token_file.read_bytes()).hexdigest()
    workload = {'workloads': [{'cell': 'semantic-computer-task-512', 'prompt_tokens': 512,
        'generate_tokens': 512, 'tokens_file': str(token_file.resolve()), 'tokens_sha256': digest,
        'messages': [{'role': 'user', 'content': prompt}],
        'chat_template_kwargs': {'enable_thinking': False}}],
        'tokenizer': str(TOKENIZER),
        'policy': 'exact 512 formatted input tokens; one natural-completion quality request, separate from timing'}
    (HERE / 'workloads.json').write_text(json.dumps(workload, indent=2) + '\n')
    print(json.dumps({'prompt_tokens': len(ids), 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                      'token_ids_sha256': digest}, indent=2))

if __name__ == '__main__': main()
