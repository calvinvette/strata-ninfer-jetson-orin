#!/usr/bin/env python3
"""Independently verify the held-out 128K retrieval/arithmetic input."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

EXPECTED = ["AMBER-QUARTZ-417", "INDIGO-MAPLE-638", "SILVER-ORBIT-925"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workload", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    workload = json.loads(args.workload.read_text())["workloads"][0]
    content = workload["messages"][0]["content"]
    rendered = ChatTemplate(args.tokenizer / "chat_template.jinja").render(
        workload["messages"], enable_thinking=False)
    actual_tokens = len(load_tokenizer(args.tokenizer).encode(rendered, parse_special=True))
    fractions = [content.index(code) / len(content) for code in EXPECTED]
    suffixes = [int(code.rsplit("-", 1)[1]) for code in EXPECTED]
    result = {
        "actual_prompt_tokens": actual_tokens,
        "declared_prompt_tokens": workload["prompt_tokens"],
        "expected_codes": EXPECTED,
        "marker_character_fractions": fractions,
        "markers_once_in_order": all(content.count(code) == 1 for code in EXPECTED)
            and fractions == sorted(fractions),
        "suffixes": suffixes,
        "oracle_sum": sum(suffixes),
    }
    result["pass"] = (actual_tokens == workload["prompt_tokens"]
        and workload["expected_codes"] == EXPECTED
        and result["markers_once_in_order"]
        and all(abs(actual - expected) <= 0.01 for actual, expected in zip(fractions, (0.1, 0.5, 0.9)))
        and result["oracle_sum"] == 1980)
    out = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(out)
    print(out, end="")
    return 0 if result["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
