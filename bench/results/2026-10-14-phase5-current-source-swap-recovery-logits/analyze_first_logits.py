#!/usr/bin/env python3
"""Compare the first-window logits from the short/long/short recovery run."""
import argparse
from array import array
import json
import math
from pathlib import Path


def read_logits(path: Path) -> array:
    values = array("f")
    with path.open("rb") as stream:
        values.fromfile(stream, path.stat().st_size // values.itemsize)
    if path.stat().st_size % values.itemsize:
        raise ValueError(f"{path}: byte length is not float32 aligned")
    if not values:
        raise ValueError(f"{path}: empty logits")
    return values


def logsumexp(values: array) -> float:
    maximum = max(values)
    return maximum + math.log(sum(math.exp(float(value) - maximum) for value in values))


def compare(first: array, recovery: array) -> dict:
    if len(first) != len(recovery):
        raise ValueError("logit vector lengths differ")
    first_norm2 = sum(float(value) ** 2 for value in first)
    recovery_norm2 = sum(float(value) ** 2 for value in recovery)
    dot = 0.0
    delta_norm2 = 0.0
    max_abs_delta = 0.0
    for left, right in zip(first, recovery):
        left = float(left)
        right = float(right)
        delta = right - left
        dot += left * right
        delta_norm2 += delta * delta
        max_abs_delta = max(max_abs_delta, abs(delta))

    first_top = max(range(len(first)), key=first.__getitem__)
    recovery_top = max(range(len(recovery)), key=recovery.__getitem__)
    first_top10 = set(sorted(range(len(first)), key=first.__getitem__, reverse=True)[:10])
    recovery_top10 = set(sorted(range(len(recovery)), key=recovery.__getitem__, reverse=True)[:10])
    first_lse = logsumexp(first)
    recovery_lse = logsumexp(recovery)
    kl_first_to_recovery = sum(
        math.exp(float(left) - first_lse)
        * (float(left) - float(right) + recovery_lse - first_lse)
        for left, right in zip(first, recovery)
    )
    kl_recovery_to_first = sum(
        math.exp(float(right) - recovery_lse)
        * (float(right) - float(left) + first_lse - recovery_lse)
        for left, right in zip(first, recovery)
    )
    return {
        "vocab": len(first),
        "bit_identical": first == recovery,
        "first_top1": first_top,
        "recovery_top1": recovery_top,
        "top1_changed": first_top != recovery_top,
        "max_abs_delta": max_abs_delta,
        "relative_l2": math.sqrt(delta_norm2 / first_norm2),
        "cosine": max(-1.0, min(1.0, dot / math.sqrt(first_norm2 * recovery_norm2))),
        "top10_overlap": len(first_top10 & recovery_top10),
        "temperature_1_kl_first_to_recovery": kl_first_to_recovery,
        "temperature_1_kl_recovery_to_first": kl_recovery_to_first,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=Path(__file__).parent / "trace")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "logit-analysis.json")
    args = parser.parse_args()
    vectors = {
        f"{arm}_{index}": read_logits(args.trace / f"{arm}-first-logits.{index}")
        for arm in ("mtp0", "mtp4") for index in (0, 1, 2)
    }
    report = {
        "scope": "first-window logits for 512 -> 2048 -> 512 adaptive-swap sequence",
        "comparisons": {
            "mtp0_first_vs_recovery": compare(vectors["mtp0_0"], vectors["mtp0_2"]),
            "mtp4_first_vs_recovery": compare(vectors["mtp4_0"], vectors["mtp4_2"]),
            "mtp0_vs_mtp4_first": compare(vectors["mtp0_0"], vectors["mtp4_0"]),
            "mtp0_vs_mtp4_recovery": compare(vectors["mtp0_2"], vectors["mtp4_2"]),
        },
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
