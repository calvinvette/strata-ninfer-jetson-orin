#!/usr/bin/env python3
"""Prepare an exact-length held-out long Q2_0 retrieval/arithmetic fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

MARKERS = (('10%', 'AMBER-QUARTZ-618'), ('50%', 'SILVER-MEADOW-243'),
           ('90%', 'INDIGO-LANTERN-907'))


def build_body(fillers: tuple[int, int, int, int]) -> str:
    parts = ['Archive record 000001: routine calibration nominal; no fault observed.\n',
             'calibration ' * fillers[0],
             f'\nRetrieval marker {MARKERS[0][0]}: the vault code is {MARKERS[0][1]}. Preserve it exactly.\n',
             'Archive record 000002: routine calibration nominal; no fault observed.\n',
             'calibration ' * fillers[1],
             f'\nRetrieval marker {MARKERS[1][0]}: the vault code is {MARKERS[1][1]}. Preserve it exactly.\n',
             'Archive record 000003: routine calibration nominal; no fault observed.\n',
             'calibration ' * fillers[2],
             f'\nRetrieval marker {MARKERS[2][0]}: the vault code is {MARKERS[2][1]}. Preserve it exactly.\n',
             'Archive record 000004: routine calibration nominal; no fault observed.\n',
             'calibration ' * fillers[3],
             '\nReturn the three vault codes in order and calculate the sum of their numeric suffixes. '
             'Use exactly EARLY=..., MIDDLE=..., LATE=..., SUM=... with no other text.']
    return ''.join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tokenizer', type=Path,
                    default=Path('/home/calvin/models/strata-orin-validation/pack/tokenizer'))
    ap.add_argument('--tokens', type=int, default=4096)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.tokens < 2048:
        ap.error('--tokens must be at least 2048 for this long-context fixture')
    a.output.mkdir(parents=True, exist_ok=False)
    tokenizer = load_tokenizer(a.tokenizer)
    template_path = a.tokenizer / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    def encode(text: str) -> list[int]:
        return tokenizer.encode(template.render([{'role': 'user', 'content': text}],
                                   enable_thinking=False), parse_special=True)

    base_count = len(encode(build_body((0, 0, 0, 0))))
    remaining = a.tokens - base_count
    weights = (0.10, 0.40, 0.40, 0.10)
    fillers = [int(remaining * weight) for weight in weights]
    fillers[-1] += remaining - sum(fillers)
    for _ in range(16):
        count = len(encode(build_body(tuple(fillers))))
        if count == a.tokens:
            break
        fillers[-1] += a.tokens - count
        if fillers[-1] < 0:
            raise RuntimeError('tokenizer correction made final filler negative')
    else:
        raise RuntimeError(f'could not make exact {a.tokens}-token prompt; last count={count}')
    body = build_body(tuple(fillers))
    ids = encode(body)
    if len(ids) != a.tokens:
        raise RuntimeError(f'final prompt has {len(ids)} tokens, expected {a.tokens}')
    workload = {'workloads': [{'cell': f'heldout-retrieval-arithmetic-{a.tokens}',
        'prompt_tokens': a.tokens, 'generate_tokens': 48,
        'messages': [{'role': 'user', 'content': body}],
        'chat_template_kwargs': {'enable_thinking': False},
        'expected_codes': [code for _, code in MARKERS], 'expected_suffix_sum': 1768,
        'allow_natural_stop': True}]}
    path = a.output / 'workload.json'
    path.write_text(json.dumps(workload, indent=2) + '\n')
    print(json.dumps({'prompt_tokens': len(ids), 'filler_counts': fillers,
        'content_sha256': hashlib.sha256(body.encode()).hexdigest(),
        'token_ids_sha256': hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest(),
        'workload_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
