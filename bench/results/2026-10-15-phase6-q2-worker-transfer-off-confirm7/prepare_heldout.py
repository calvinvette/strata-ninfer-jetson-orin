#!/usr/bin/env python3
"""Create a held-out, exact-512-token Q2_0 retrieval and arithmetic task."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

MARKERS = (
    ('10%', 'JADE-COMET-482'),
    ('50%', 'CRIMSON-DELTA-137'),
    ('90%', 'PEARL-FOREST-809'),
)


def build_body(filler_counts):
    parts = ['Archive record 000001: routine calibration nominal; no fault observed.\n']
    parts.append('calibration ' * filler_counts[0])
    parts.append(f'\nRetrieval marker {MARKERS[0][0]}: the vault code is {MARKERS[0][1]}. Preserve it exactly.\n')
    parts.append('Archive record 000002: routine calibration nominal; no fault observed.\n')
    parts.append('calibration ' * filler_counts[1])
    parts.append(f'\nRetrieval marker {MARKERS[1][0]}: the vault code is {MARKERS[1][1]}. Preserve it exactly.\n')
    parts.append('Archive record 000003: routine calibration nominal; no fault observed.\n')
    parts.append('calibration ' * filler_counts[2])
    parts.append(f'\nRetrieval marker {MARKERS[2][0]}: the vault code is {MARKERS[2][1]}. Preserve it exactly.\n')
    parts.append('Archive record 000004: routine calibration nominal; no fault observed.\n')
    parts.append('calibration ' * filler_counts[3])
    parts.append('\nReturn the three vault codes in order and calculate the sum of their numeric suffixes. '
                 'Use exactly EARLY=..., MIDDLE=..., LATE=..., SUM=... with no other text.')
    return ''.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path,
                        default=Path('/home/calvin/models/strata-orin-validation/pack/tokenizer'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    tokenizer = load_tokenizer(args.tokenizer)
    template_path = args.tokenizer / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')

    def encode(text):
        rendered = template.render([{'role': 'user', 'content': text}], enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    # Distribute filler in four intervals, placing markers near 10/50/90%.
    base = build_body((0, 0, 0, 0))
    remaining = 512 - len(encode(base))
    if remaining < 0:
        raise RuntimeError('retrieval task text already exceeds 512 tokens')
    weights = (0.10, 0.40, 0.40, 0.10)
    filler = tuple(int(remaining * weight) for weight in weights)
    filler = (*filler[:3], filler[3] + remaining - sum(filler))
    for _ in range(8):
        body = build_body(filler)
        count = len(encode(body))
        if count == 512:
            break
        delta = 512 - count
        # Correct any tokenizer boundary merges at the final filler interval.
        filler = (*filler[:3], filler[3] + delta)
    else:
        raise RuntimeError(f'failed to make exact 512-token prompt; got {count}')

    body = build_body(filler)
    count = len(encode(body))
    if count != 512:
        raise RuntimeError(f'prompt rendered to {count} tokens instead of 512')
    workload = {
        'workloads': [{
            'cell': 'heldout-retrieval-arithmetic-512',
            'prompt_tokens': count,
            'generate_tokens': 48,
            'messages': [{'role': 'user', 'content': body}],
            'chat_template_kwargs': {'enable_thinking': False},
            'expected_codes': [code for _, code in MARKERS],
            'expected_suffix_sum': sum(int(code.rsplit('-', 1)[1]) for _, code in MARKERS),
            'allow_natural_stop': True,
        }]
    }
    output = args.output / 'workloads.json'
    output.write_text(json.dumps(workload, indent=2) + '\n')
    summary = {'prompt_tokens': count, 'filler_counts': filler,
               'codes': dict(MARKERS), 'expected_suffix_sum': sum(int(code.rsplit('-', 1)[1]) for _, code in MARKERS),
               'workloads_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    (args.output / 'prepared.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
