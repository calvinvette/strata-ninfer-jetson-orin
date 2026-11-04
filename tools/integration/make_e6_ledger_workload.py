#!/usr/bin/env python3
"""Create a tokenizer-verified 2,048-token ledger aggregation workload."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from prepare_controls import load_tokenizer  # noqa: E402
from serve.frontend import ChatTemplate  # noqa: E402


LEDGER_TASK = '''Task: audit the ledger below. For each region, calculate the number of records, sum of signed amounts, the ID of the record with the highest amount, and that highest amount. Also calculate the total record count and total signed sum. Include each region that appears. Return only valid JSON with this shape: {"regions":{"EAST":{"count":0,"sum":0,"max_id":"","max_amount":0},"NORTH":{},"WEST":{}},"total":{"count":0,"sum":0}}. Use the exact IDs and include negative amounts in sums.
Ledger records (id, region, amount):
R01 EAST 14
R02 WEST 9
R03 EAST 5
R04 NORTH 12
R05 WEST -3
R06 EAST 8
R07 NORTH 2
R08 WEST 11
R09 EAST -4
R10 NORTH 7
R11 WEST 6
R12 EAST 13
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt-tokens", type=int, default=2048)
    parser.add_argument("--generate-tokens", type=int, default=128)
    args = parser.parse_args()

    tokenizer = load_tokenizer(args.tokenizer)
    template = ChatTemplate(args.tokenizer / "chat_template.jinja")

    def encode(text: str) -> list[int]:
        rendered = template.render([{"role": "user", "content": text}], enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    low, high = 0, args.prompt_tokens
    found = None
    while low <= high:
        count = (low + high) // 2
        content = "red " * count + LEDGER_TASK
        actual = len(encode(content))
        if actual == args.prompt_tokens:
            found = content
            break
        if actual < args.prompt_tokens:
            low = count + 1
        else:
            high = count - 1
    if found is None:
        raise SystemExit(f"could not construct exactly {args.prompt_tokens} formatted tokens")

    token_ids = encode(found)
    payload = {"workloads": [{
        "cell": "heldout-ledger-aggregation-2048",
        "prompt_tokens": args.prompt_tokens,
        "generate_tokens": args.generate_tokens,
        "allow_natural_stop": True,
        "messages": [{"role": "user", "content": found}],
        "chat_template_kwargs": {"enable_thinking": False},
    }]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2) + "\n").encode()
    args.output.write_bytes(encoded)
    print(json.dumps({"output": str(args.output), "prompt_tokens": len(token_ids),
                      "token_ids_sha256": hashlib.sha256(
                          ",".join(map(str, token_ids)).encode()).hexdigest(),
                      "workload_file_sha256": hashlib.sha256(encoded).hexdigest()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
