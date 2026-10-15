#!/usr/bin/env python3
"""Prepare a held-out near-limit Q2_0 retrieval prompt and hash it."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

NEEDLES = (("10%", "COPPER-FERN-482"), ("50%", "NORTH-EMBER-619"),
           ("90%", "SILVER-OTTER-357"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path,
                        default=Path("/home/calvin/models/strata-orin-validation/pack/tokenizer"))
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty output directory: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)
    tokenizer = load_tokenizer(args.tokenizer)
    template_path = args.tokenizer / "chat_template.jinja"
    template = ChatTemplate(template_path if template_path.exists() else ROOT / "serve/chat_template.jinja")

    def encode(text):
        rendered = template.render([{"role": "user", "content": text}], enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    def body(rows):
        cuts = [round(rows * fraction) for fraction in (0.10, 0.50, 0.90)]
        parts, start = [], 0
        for (label, code), cut in zip(NEEDLES, cuts):
            parts.extend(f"Archive entry {i:06d}: routine sensor status nominal; no alarm observed.\n"
                         for i in range(start, cut))
            parts.append(f"\nRetrieval marker {label}: the vault key is {code}. Preserve this exact key.\n")
            start = cut
        parts.extend(f"Archive entry {i:06d}: routine sensor status nominal; no alarm observed.\n"
                     for i in range(start, rows))
        parts.append("\nReturn the three vault keys in order as EARLY=..., MIDDLE=..., LATE=... with no other text.")
        return "".join(parts)

    target = args.context - max(600, args.context // 12)
    low, high, best = 0, target * 2, None
    while low <= high:
        rows = (low + high) // 2
        text = body(rows)
        count = len(encode(text))
        if count <= target:
            best = (count, text, rows)
            low = rows + 1
        else:
            high = rows - 1
    if best is None or best[0] < target - 32 or best[0] + 64 >= args.context:
        raise RuntimeError(f"failed to prepare safe near-limit prompt: {best and best[0]} tokens")
    count, text, rows = best
    workload = {"workloads": [{
        "cell": f"heldout-int8-mtp3-multineedle-{args.context}",
        "prompt_tokens": count, "generate_tokens": 48,
        "messages": [{"role": "user", "content": text}],
        "chat_template_kwargs": {"enable_thinking": False},
        "expected_codes": [code for _, code in NEEDLES],
        "allow_natural_stop": True,
    }]}
    path = args.output / f"workload-{args.context}.json"
    path.write_text(json.dumps(workload, indent=2) + "\n")
    summary = {"context": args.context, "target_prompt_tokens": target,
               "actual_prompt_tokens": count, "filler_rows": rows,
               "workload": path.name,
               "workload_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "markers": dict(NEEDLES)}
    (args.output / "prepared.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
