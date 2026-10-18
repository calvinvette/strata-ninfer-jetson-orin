#!/usr/bin/env python3
"""Create an exact near-8K Q2_0 retrieval workload with held-out markers."""
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
    ("10%", "BRONZE-PINE-582"),
    ("50%", "VIOLET-CANYON-146"),
    ("90%", "CRIMSON-HARBOR-839"),
)


def make_body(rows):
    cuts = [round(rows * p) for p in (0.10, 0.50, 0.90)]
    parts = []
    start = 0
    for (label, code), cut in zip(NEEDLES, cuts):
        for i in range(start, cut):
            parts.append(f"Archive record {i:06d}: routine sensor status nominal; no alarm observed.\n")
        parts.append(f"\nRetrieval marker {label}: the vault key is {code}. Preserve this exact key.\n")
        start = cut
    for i in range(start, rows):
        parts.append(f"Archive record {i:06d}: routine sensor status nominal; no alarm observed.\n")
    parts.append("\nReturn the three vault keys in order as EARLY=..., MIDDLE=..., LATE=... with no other text.")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tokenizer", type=Path, default=Path("/home/calvin/models/strata-orin-validation/pack/tokenizer"))
    ap.add_argument("--context", type=int, default=8192)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    tok = load_tokenizer(a.tokenizer)
    template_path = a.tokenizer / "chat_template.jinja"
    template = ChatTemplate(template_path if template_path.exists() else ROOT / "serve/chat_template.jinja")

    def encode(text):
        rendered = template.render([{"role": "user", "content": text}], enable_thinking=False)
        return tok.encode(rendered, parse_special=True)

    target = a.context - max(600, a.context // 12)
    lo, hi, best = 0, target * 2, None
    while lo <= hi:
        mid = (lo + hi) // 2
        body = make_body(mid)
        count = len(encode(body))
        if count <= target:
            best = (count, body, mid)
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None or best[0] < target - 32 or best[0] + 64 >= a.context:
        raise RuntimeError(f"unable to construct a safe near-limit workload for context={a.context}: {best and best[0]}")
    count, body, rows = best
    workload = {
        "workloads": [{
            "cell": f"heldout-multineedle-{a.context}",
            "prompt_tokens": count,
            "generate_tokens": 48,
            "messages": [{"role": "user", "content": body}],
            "chat_template_kwargs": {"enable_thinking": False},
            "expected_codes": [code for _, code in NEEDLES],
            "allow_natural_stop": True,
        }]
    }
    path = a.output / f"workload-{a.context}.json"
    path.write_text(json.dumps(workload, indent=2) + "\n")
    summary = {"context": a.context, "target_prompt_tokens": target,
               "actual_prompt_tokens": count, "filler_rows": rows,
               "workload": path.name,
               "workload_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "markers": dict(NEEDLES)}
    (a.output / "prepared.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
