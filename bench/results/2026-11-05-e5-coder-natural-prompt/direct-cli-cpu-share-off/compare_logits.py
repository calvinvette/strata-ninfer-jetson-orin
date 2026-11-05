#!/usr/bin/env python3
"""Summarize the paired first-logit dumps from the direct CLI diagnostic."""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
import re
from pathlib import Path


def load(path: Path) -> tuple[list[float], str]:
    raw = path.read_bytes()
    values = array.array('f')
    values.frombytes(raw)
    if len(values) * values.itemsize != len(raw):
        raise ValueError(f'{path}: not a whole number of float32 values')
    return list(values), hashlib.sha256(raw).hexdigest()


def output_token(path: Path) -> int:
    match = re.search(r'^output\s+:\s+(\d+)\s*$', path.read_text(), re.M)
    if not match:
        raise ValueError(f'{path}: could not identify generated token')
    return int(match.group(1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strata-logits', type=Path, required=True)
    ap.add_argument('--ninfer-logits', type=Path, required=True)
    ap.add_argument('--strata-stdout', type=Path, required=True)
    ap.add_argument('--ninfer-stdout', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    s, sh = load(args.strata_logits)
    n, nh = load(args.ninfer_logits)
    if len(s) != len(n):
        raise SystemExit('logit vector lengths differ')
    def top(v: list[float]) -> list[dict]:
        ids = sorted(range(len(v)), key=v.__getitem__, reverse=True)[:10]
        return [{'token_id': i, 'logit': v[i]} for i in ids]
    delta = [b - a for a, b in zip(s, n)]
    l2 = math.sqrt(math.fsum(x*x for x in delta))
    norm = math.sqrt(math.fsum(x*x for x in s))
    s_top, n_top = top(s), top(n)
    result = {
        'scope': 'one direct CLI token-ID prompt; not service GEN or a performance result',
        'prompt_token_ids': [1, 2, 3],
        'prefill_cpu_share': 0,
        'logit_count': len(s),
        'strata': {'dump_sha256': sh, 'output_token': output_token(args.strata_stdout),
                   'top10': s_top, 'top1_margin': s_top[0]['logit'] - s_top[1]['logit']},
        'ninfer': {'dump_sha256': nh, 'output_token': output_token(args.ninfer_stdout),
                   'top10': n_top, 'top1_margin': n_top[0]['logit'] - n_top[1]['logit']},
        'comparison': {'output_token_equal': output_token(args.strata_stdout) == output_token(args.ninfer_stdout),
                       'different_logits': sum(a != b for a, b in zip(s, n)),
                       'relative_l2': l2 / max(norm, 1e-300),
                       'max_abs': max(map(abs, delta), default=0.0),
                       'rms_abs': math.sqrt(math.fsum(x*x for x in delta) / len(delta)),
                       'top1_equal': s_top[0]['token_id'] == n_top[0]['token_id']},
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
