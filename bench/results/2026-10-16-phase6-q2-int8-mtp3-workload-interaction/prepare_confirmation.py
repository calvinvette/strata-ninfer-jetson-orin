#!/usr/bin/env python3
"""Prepare distinct exact-length prompts for held-out interaction confirmation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from campaign_plan import workload_filename

NEEDLES = {
    "short": (("10%", "CITRUS-AXLE-431"),
              ("50%", "MARBLE-THICKET-782"),
              ("90%", "OXIDE-KITE-265")),
    "near_limit": (("10%", "PLUM-STATIC-614"),
                   ("50%", "GLACIER-KEY-203"),
                   ("90%", "FENNEL-ORBIT-589")),
}
TARGETS = {"short": 512, "near_limit": 7501}


def make_body(rows, markers, padding_words, workload):
    cuts = [round(rows * fraction) for fraction in (0.10, 0.50, 0.90)]
    parts = ["Independent held-out service trace.\n"]
    start = 0
    for (label, code), cut in zip(markers, cuts):
        parts.extend(f"Archive row {index:05d}: routine sensor state nominal.\n"
                     for index in range(start, cut))
        parts.append(f"\nRetrieval marker {label}: preserve key {code} exactly.\n")
        start = cut
    parts.extend(f"Archive row {index:05d}: routine sensor state nominal.\n"
                 for index in range(start, rows))
    if padding_words:
        parts.append("\nAdditional ordinary record: " + "routine " * padding_words + "\n")
    if workload == "short":
        parts.append("\nReturn the three marker codes in order. Also add the three numbers at the ends of those codes. Output exactly: EARLY=<first full code>, MIDDLE=<second full code>, LATE=<third full code>, SUM=<sum of the three ending numbers>.")
    else:
        parts.append("\nReturn the three keys in order as EARLY=..., MIDDLE=..., LATE=... with no other text.")
    return "".join(parts)


def exact_workload(name, encode):
    target = TARGETS[name]
    markers = NEEDLES[name]
    low, high, best_rows = 0, target * 2, None
    while low <= high:
        rows = (low + high) // 2
        count = len(encode(make_body(rows, markers, 0, name)))
        if count <= target:
            best_rows = rows
            low = rows + 1
        else:
            high = rows - 1
    if best_rows is None:
        raise RuntimeError(f"fixed prompt material exceeds {target} tokens for {name}")
    for padding_words in range(0, 96):
        text = make_body(best_rows, markers, padding_words, name)
        if len(encode(text)) == target:
            workload = {
                "workloads": [{
                    "cell": f"mtp-workload-interaction-{name}",
                    "prompt_tokens": target,
                    "generate_tokens": 48,
                    "messages": [{"role": "user", "content": text}],
                    "chat_template_kwargs": {"enable_thinking": False},
                    "expected_codes": [code for _, code in markers],
                    "allow_natural_stop": True,
                }]
            }
            if name == "short":
                workload["workloads"][0]["expected_suffix_sum"] = 1478
            return workload, best_rows, padding_words
    raise RuntimeError(f"could not make an exact {target}-token {name} prompt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path,
                        default=Path("/home/calvin/models/strata-orin-validation/pack/tokenizer"))
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "confirmation")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    tokenizer = load_tokenizer(args.tokenizer)
    template_path = args.tokenizer / "chat_template.jinja"
    template = ChatTemplate(template_path if template_path.exists()
                            else ROOT / "serve/chat_template.jinja")

    def encode(content):
        rendered = template.render([{"role": "user", "content": content}],
                                   enable_thinking=False)
        return tokenizer.encode(rendered, parse_special=True)

    manifest = {"tokenizer": str(args.tokenizer), "template": str(template_path),
                "target_prompt_tokens": TARGETS, "workloads": {}}
    generated = {}
    for name in ("short", "near_limit"):
        workload, rows, padding = exact_workload(name, encode)
        filename = workload_filename(name)
        generated[filename] = workload
        manifest["workloads"][name] = {
            "path": filename,
            "actual_prompt_tokens": workload["workloads"][0]["prompt_tokens"],
            "filler_rows": rows,
            "padding_words": padding,
            "sha256": hashlib.sha256((json.dumps(workload, indent=2) + "\n").encode()).hexdigest(),
            "markers": dict(NEEDLES[name]),
        }
    args.output.mkdir(parents=True)
    for filename, workload in generated.items():
        (args.output / filename).write_text(json.dumps(workload, indent=2) + "\n")
    (args.output / "prepared.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
