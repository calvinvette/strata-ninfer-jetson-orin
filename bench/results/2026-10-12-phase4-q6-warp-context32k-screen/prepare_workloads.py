#!/usr/bin/env python3
"""Create exact-length synthetic incident and distinct warm-up requests."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from strata_tokenizer import Tokenizer
from serve.frontend import ChatTemplate

TOKENIZER = Path("/home/calvin/models/strata-orin-validation/pack/tokenizer")
OUTPUT = Path(__file__).resolve().parent
vocab = json.loads((TOKENIZER / "vocab.json").read_text())
tokens = [None] * len(vocab)
for text, index in vocab.items():
    tokens[index] = text
tok = Tokenizer(tokens, (TOKENIZER / "merges.txt").read_text().split("\n"),
                json.loads((TOKENIZER / "token_type.json").read_text()))
template = ChatTemplate(TOKENIZER / "chat_template.jinja")


def encode(content):
    return tok.encode(template.render([{"role": "user", "content": content}],
                                      enable_thinking=False), parse_special=True)


def exact(target, prefix, filler, suffix):
    low, high = 0, target
    while low <= high:
        count = (low + high) // 2
        content = prefix + filler * count + suffix
        ids = encode(content)
        if len(ids) == target:
            return content, ids
        if len(ids) < target:
            low = count + 1
        else:
            high = count - 1
    raise RuntimeError(f"cannot construct exact {target}-token prompt")


events = " ".join(
    f"{hour:02d}:{minute:02d} service={service} zone={zone} p95={latency}ms errors={errors} "
    f"retries={retries} deploy={deploy}."
    for i, (hour, minute, service, zone, latency, errors, retries, deploy) in enumerate([
        (9, 0, "gateway", "north", 42, 0, 1, "none"),
        (9, 5, "search", "north", 88, 1, 2, "build71"),
        (9, 10, "cache", "north", 310, 8, 19, "none"),
        (9, 15, "gateway", "south", 49, 0, 1, "none"),
        (9, 20, "search", "south", 91, 0, 2, "build71"),
        (9, 25, "cache", "south", 295, 7, 17, "none"),
        (9, 30, "gateway", "north", 45, 0, 1, "none"),
        (9, 35, "search", "north", 95, 1, 2, "build71"),
        (9, 40, "cache", "north", 322, 9, 21, "none"),
        (9, 45, "gateway", "south", 47, 0, 1, "none"),
        (9, 50, "search", "south", 87, 0, 2, "build71"),
        (9, 55, "cache", "south", 301, 8, 18, "none"),
    ])
)
routine = "10:00 service=metrics zone=east p95=52ms errors=0 retries=1 deploy=none. "
measured, measured_ids = exact(
    2048, "Field incident log: " + events + " " + routine,
    " x",
    " Report only patterns supported by the log. Separate observation from cause, identify "
    "one plausible confounder, and propose a measurement that could distinguish it. Write "
    "at least 250 words.")
warmup, warmup_ids = exact(
    172, "Warm-up maintenance note: ", " x",
    " Explain why a timestamp and calibration record help interpret later readings.")


def write(name, cell, prompt, ids, generated):
    token_path = OUTPUT / f"{name}.tokens"
    token_path.write_text(",".join(map(str, ids)) + "\n")
    return {"workloads": [{"cell": cell, "prompt_tokens": len(ids),
                           "generate_tokens": generated,
                           "tokens_file": str(token_path.resolve()),
                           "tokens_sha256": hashlib.sha256(token_path.read_bytes()).hexdigest(),
                           "messages": [{"role": "user", "content": prompt}],
                           "chat_template_kwargs": {"enable_thinking": False}}],
            "tokenizer": [{"path": str((TOKENIZER / name).resolve()),
                           "sha256": hashlib.sha256((TOKENIZER / name).read_bytes()).hexdigest()}
                          for name in ("vocab.json", "merges.txt", "token_type.json", "chat_template.jinja")],
            "policy": "exact formatted input verified using Strata tokenizer and chat template; API usage is rechecked per cell"}


(OUTPUT / "workloads.json").write_text(json.dumps(
    write("measured", "heldout-context32k-2048", measured, measured_ids, 128), indent=2) + "\n")
(OUTPUT / "warmup-workloads.json").write_text(json.dumps(
    write("warmup", "distinct-warmup-172", warmup, warmup_ids, 64), indent=2) + "\n")
print(json.dumps({"prompt_tokens": len(measured_ids), "warmup_tokens": len(warmup_ids),
                  "prompt_sha256": hashlib.sha256((OUTPUT / "measured.tokens").read_bytes()).hexdigest(),
                  "warmup_sha256": hashlib.sha256((OUTPUT / "warmup.tokens").read_bytes()).hexdigest()}, indent=2))
