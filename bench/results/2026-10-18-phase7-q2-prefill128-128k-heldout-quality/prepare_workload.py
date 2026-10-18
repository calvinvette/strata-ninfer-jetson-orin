#!/usr/bin/env python3
"""Generate a near-limit, held-out 128K retrieval-plus-arithmetic task."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

NEEDLES = (("10%", "AMBER-QUARTZ-417"),
           ("50%", "INDIGO-MAPLE-638"),
           ("90%", "SILVER-ORBIT-925"))

def body(rows: int) -> str:
    cuts = [round(rows * p) for p in (0.10, 0.50, 0.90)]
    parts = []
    start = 0
    for (label, code), cut in zip(NEEDLES, cuts):
        parts.extend(f"Log record {i:06d}: routine calibration nominal; no fault observed.\n"
                     for i in range(start, cut))
        parts.append(f"\nRetrieval marker {label}: the secret code is {code}. Remember this exact code.\n")
        start = cut
    parts.extend(f"Log record {i:06d}: routine calibration nominal; no fault observed.\n"
                 for i in range(start, rows))
    parts.append("\nReturn the three secret codes in order as EARLY=..., MIDDLE=..., LATE=..., then add their numeric suffixes and return SUM=... . Use no other text.")
    return "".join(parts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tokenizer', type=Path, required=True)
    ap.add_argument('--context', type=int, default=131072)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    tok = load_tokenizer(args.tokenizer)
    template = ChatTemplate(args.tokenizer / 'chat_template.jinja')
    target = args.context - max(600, args.context // 12)
    def encode(rows):
        messages = [{'role':'user','content':body(rows)}]
        rendered = template.render(messages, enable_thinking=False)
        return len(tok.encode(rendered, parse_special=True)), messages
    lo, hi, best = 0, target * 2, None
    while lo <= hi:
        mid = (lo + hi) // 2
        count, messages = encode(mid)
        if count <= target:
            best = (count, messages, mid)
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None or best[0] < target - 32 or best[0] + 64 >= args.context:
        raise RuntimeError(f'could not fit target context: {best and best[0]} / {args.context}')
    count, messages, rows = best
    workload = {'cell':'heldout-retrieval-arithmetic-128k', 'prompt_tokens':count,
                'generate_tokens':64, 'messages':messages,
                'chat_template_kwargs':{'enable_thinking':False},
                'expected_codes':[code for _,code in NEEDLES]}
    args.output.write_text(json.dumps({'workloads':[workload]},indent=2)+'\n')
    print(json.dumps({'context':args.context,'prompt_tokens':count,'rows':rows,
                      'codes':workload['expected_codes'],
                      'oracle_sum':sum(int(code.rsplit('-',1)[1]) for _,code in NEEDLES),
                      'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))
if __name__ == '__main__': main()
