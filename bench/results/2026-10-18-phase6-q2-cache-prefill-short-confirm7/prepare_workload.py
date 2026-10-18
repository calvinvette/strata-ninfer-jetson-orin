#!/usr/bin/env python3
"""Build a fresh exact-512-token retrieval-plus-sum task for the short-prompt confirmation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

CODES = ("TUNDRA-ORBIT-593", "COBALT-MAPLE-248", "GRANITE-COMET-761")
EXPECTED_SUM = sum(int(code.rsplit("-", 1)[1]) for code in CODES)


def body(rows):
    cuts = [round(rows * p) for p in (0.10, 0.50, 0.90)]
    parts = ["Independent short-task cache/prefill confirmation.\n"]
    start = 0
    for label, code, cut in zip(("10%", "50%", "90%"), CODES, cuts):
        for i in range(start, cut):
            parts.append(f"Archive row {i:04d}: routine sensor state nominal.\n")
        parts.append(f"Retrieval marker {label}: preserve key {code} exactly.\n")
        start = cut
    for i in range(start, rows):
        parts.append(f"Archive row {i:04d}: routine sensor state nominal.\n")
    parts.append(
        "Return all three marker codes in order and add their numeric suffixes. "
        "Output exactly: EARLY=<first full code>, MIDDLE=<second full code>, "
        "LATE=<third full code>, SUM=<sum>."
    )
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tokenizer", type=Path, default=Path("/home/calvin/models/strata-orin-validation/pack/tokenizer"))
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    tok = load_tokenizer(a.tokenizer)
    template_path = a.tokenizer / "chat_template.jinja"
    template = ChatTemplate(template_path if template_path.exists() else ROOT / "serve/chat_template.jinja")

    def encode(text):
        rendered = template.render([{"role": "user", "content": text}], enable_thinking=False)
        return tok.encode(rendered, parse_special=True)

    lo, hi, best = 0, 512, None
    while lo <= hi:
        rows = (lo + hi) // 2
        text = body(rows)
        count = len(encode(text))
        if count <= 512:
            best = (rows, text, count)
            lo = rows + 1
        else:
            hi = rows - 1
    if best is None or best[2] != 512:
        raise RuntimeError(f"could not construct exactly 512 prompt tokens; got {best and best[2]}")
    rows, text, count = best
    workload = {"workloads": [{
        "cell": "heldout-cache-prefill-short-retrieval-sum",
        "prompt_tokens": count,
        "generate_tokens": 48,
        "messages": [{"role": "user", "content": text}],
        "chat_template_kwargs": {"enable_thinking": False},
        "expected_codes": list(CODES),
        "expected_suffix_sum": EXPECTED_SUM,
        "allow_natural_stop": True,
    }]}
    path = a.output / "workload.json"
    path.write_text(json.dumps(workload, indent=2) + "\n")
    (a.output / "prepared.json").write_text(json.dumps({
        "prompt_tokens": count,
        "filler_rows": rows,
        "workload_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "expected_codes": list(CODES),
        "suffix_sum": EXPECTED_SUM,
        "sum_calculation": "593 + 248 + 761 = 1602",
    }, indent=2) + "\n")
    print((a.output / "prepared.json").read_text(), end="")


if __name__ == "__main__":
    main()
