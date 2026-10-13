#!/usr/bin/env python3
"""Prepare exact-token multi-position retrieval workloads for the IQ1_M tokenizer."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

NEEDLES = (
    ("10%", "MAPLE-ORBIT-731"),
    ("50%", "COBALT-HARBOR-284"),
    ("90%", "VELVET-COPPER-956"),
)


def make_body(rows: int) -> str:
    cuts = [max(0, min(rows, round(rows * p))) for p in (0.10, 0.50, 0.90)]
    inserts = [f"\nRetrieval marker {label}: the secret code is {code}. Remember this exact code.\n"
               for label, code in NEEDLES]
    parts = []
    start = 0
    for cut, insert in zip(cuts, inserts):
        for i in range(start, cut):
            parts.append(f"Log record {i:06d}: routine calibration nominal; no fault observed.\n")
        parts.append(insert)
        start = cut
    for i in range(start, rows):
        parts.append(f"Log record {i:06d}: routine calibration nominal; no fault observed.\n")
    parts.append("\nReturn the three secret codes in order as EARLY=..., MIDDLE=..., LATE=... with no other text.")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contexts", default="8192,16384,32768")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    tok = load_tokenizer(args.tokenizer)
    template = ChatTemplate(args.tokenizer / "chat_template.jinja")
    cases = []
    for context in map(int, args.contexts.split(",")):
        target = context - max(600, context // 12)

        def encode(rows):
            messages = [{"role": "user", "content": make_body(rows)}]
            rendered = template.render(messages, enable_thinking=False)
            return len(tok.encode(rendered, parse_special=True)), messages

        lo, hi = 0, max(32, target * 2)
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            count, messages = encode(mid)
            if count <= target:
                best = (count, messages, mid)
                lo = mid + 1
            else:
                hi = mid - 1
        if best is None or best[0] < target - 32:
            raise RuntimeError(f"could not build near-limit prompt for context {context}: {best and best[0]}")
        count, messages, rows = best
        if count + 64 >= context:
            raise RuntimeError(f"insufficient output room: context={context}, prompt={count}")
        workload = {
            "cell": f"multineedle-{context}",
            "prompt_tokens": count,
            "generate_tokens": 48,
            "messages": messages,
            "chat_template_kwargs": {"enable_thinking": False},
            "expected_codes": [code for _, code in NEEDLES],
        }
        path = args.output / f"workload-{context}.json"
        path.write_text(json.dumps({"workloads": [workload]}, indent=2) + "\n")
        cases.append({"context": context, "target_prompt_tokens": target,
                      "actual_prompt_tokens": count, "filler_rows": rows,
                      "workload": path.name,
                      "workload_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "needles": dict(NEEDLES)})
    (args.output / "prepared.json").write_text(json.dumps({"cases": cases}, indent=2) + "\n")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
