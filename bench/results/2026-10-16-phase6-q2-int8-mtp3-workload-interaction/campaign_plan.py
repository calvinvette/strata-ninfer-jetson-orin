#!/usr/bin/env python3
"""Create a randomized, balanced schedule for the Q2_0 MTP × workload design."""
import argparse
import json
import random
from pathlib import Path


WORKLOADS = ("short", "near_limit")
VARIANTS = ("baseline", "candidate")
DEFAULT_SEED = 20261016


def make_schedule(repetitions, seed=DEFAULT_SEED):
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    rng = random.Random(seed)
    pairs = [(workload, replicate) for workload in WORKLOADS
             for replicate in range(repetitions)]
    rng.shuffle(pairs)
    schedule = []
    for block, (workload, replicate) in enumerate(pairs):
        variants = list(VARIANTS)
        rng.shuffle(variants)
        for variant in variants:
            schedule.append({"block": block, "workload": workload,
                             "replicate": replicate, "variant": variant})
    validate_schedule(schedule, repetitions)
    return schedule


def validate_schedule(schedule, repetitions):
    expected = {(workload, replicate) for workload in WORKLOADS
                for replicate in range(repetitions)}
    grouped = {}
    for row in schedule:
        key = (row["workload"], row["replicate"])
        grouped.setdefault(key, []).append(row)
    if set(grouped) != expected:
        raise ValueError("schedule does not cover every workload/replicate pair")
    blocks = set()
    for key, rows in grouped.items():
        if len(rows) != 2 or {row["variant"] for row in rows} != set(VARIANTS):
            raise ValueError(f"unpaired or duplicated arms for {key}")
        ids = {row["block"] for row in rows}
        if len(ids) != 1 or next(iter(ids)) in blocks:
            raise ValueError("block IDs must be unique per workload pair")
        blocks.update(ids)
    if len(schedule) != len(expected) * 2:
        raise ValueError("unexpected schedule size")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, choices=(3, 7), required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = {"seed": args.seed, "repetitions_per_workload": args.repetitions,
            "workloads": list(WORKLOADS), "variants": list(VARIANTS),
            "schedule": make_schedule(args.repetitions, args.seed)}
    rendered = json.dumps(plan, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
