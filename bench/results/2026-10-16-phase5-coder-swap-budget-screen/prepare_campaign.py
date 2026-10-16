#!/usr/bin/env python3
"""Prepare a randomized three-block Coder adaptive-swap-budget screen."""
import argparse
import json
import random
from pathlib import Path

ARMS = (
    {"name": "delayed-control", "adapt_every": 100000, "adapt_swaps": 96},
    {"name": "swap-1", "adapt_every": 4, "adapt_swaps": 1},
    {"name": "swap-8", "adapt_every": 4, "adapt_swaps": 8},
    {"name": "swap-96", "adapt_every": 4, "adapt_swaps": 96},
)


def make_schedule(seed=20261016, repetitions=3):
    rng = random.Random(seed)
    schedule = []
    for block in range(repetitions):
        order = list(ARMS)
        rng.shuffle(order)
        schedule.extend({"block": block, **arm} for arm in order)
    assert len(schedule) == repetitions * len(ARMS)
    assert all(sum(row["name"] == arm["name"] for row in schedule) == repetitions for arm in ARMS)
    return schedule


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"seed": args.seed, "repetitions_per_arm": 3, "arms": list(ARMS),
              "schedule": make_schedule(args.seed)}
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
