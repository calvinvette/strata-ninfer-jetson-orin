"""Prepare exact formatted Coder control inputs without starting an engine."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from serve.frontend import ChatTemplate
from strata_tokenizer import Tokenizer
from control_manifest import digest


def load_tokenizer(path):
    vocab = json.loads((path / 'vocab.json').read_text())
    tokens = [None] * len(vocab)
    for text, index in vocab.items():
        tokens[index] = text
    return Tokenizer(tokens, (path / 'merges.txt').read_text().split('\n'),
                     json.loads((path / 'token_type.json').read_text()))


def exact_prompt(target, encode):
    # Search content length, never truncate the template's assistant prefix.
    prefix = 'Context: '
    suffix = '\nWrite at least 200 words explaining how a computer processes information. Start with the processor.'
    low, high = 0, target
    while low <= high:
        count = (low + high) // 2
        text = prefix + 'red ' * count + suffix
        actual = len(encode(text))
        if actual == target:
            return text
        if actual < target:
            low = count + 1
        else:
            high = count - 1
    raise ValueError(f'cannot construct exactly {target} tokens using this template/tokenizer')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tok = load_tokenizer(args.tokenizer)
    template = ChatTemplate(args.tokenizer / 'chat_template.jinja')
    def encode(text):
        rendered = template.render([{'role': 'user', 'content': text}], enable_thinking=False)
        return tok.encode(rendered, parse_special=True)
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for target, generated in [(512, 64), (2048, 128)]:
        text = exact_prompt(target, encode)
        ids = encode(text)
        path = args.output / f'pp{target}-tg{generated}.tokens'
        path.write_text(','.join(map(str, ids)) + '\n')
        rows.append({'cell': f'pp{target}+tg{generated}', 'prompt_tokens': len(ids),
                     'generate_tokens': generated, 'tokens_file': str(path.resolve()),
                     'tokens_sha256': digest(path), 'messages': [{'role': 'user', 'content': text}],
                     'chat_template_kwargs': {'enable_thinking': False}})
    for repeat in (32, 128, 256):
        text = f'Experiment 0, size {repeat}. Context: ' + 'red green blue yellow ' * repeat
        text += '\nWrite at least 200 words explaining how a computer processes information. Start with the processor.'
        rows.append({'cell': f'historical-repeat-{repeat}', 'prompt_tokens': len(encode(text)),
                     'generate_tokens': 64, 'messages': [{'role': 'user', 'content': text}],
                     'chat_template_kwargs': {'enable_thinking': False}})
    files = ['vocab.json', 'merges.txt', 'token_type.json', 'chat_template.jinja']
    (args.output / 'workloads.json').write_text(json.dumps({'workloads': rows,
        'tokenizer': [{'path': str((args.tokenizer / f).resolve()), 'sha256': digest(args.tokenizer / f)} for f in files],
        'policy': 'exact formatted inputs; CLI timings treat last prompt token in decode; API counts must be rechecked'}, indent=2) + '\n')
    print(json.dumps([{k: row[k] for k in ('cell', 'prompt_tokens', 'generate_tokens')} for row in rows], indent=2))


if __name__ == '__main__':
    main()
