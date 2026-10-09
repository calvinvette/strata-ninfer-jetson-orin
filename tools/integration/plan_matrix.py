#!/usr/bin/env python3
"""Enumerate a proposed campaign; never execute engines or claim capabilities."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]


def positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def build_plan(config, selected=None, confirmation=False):
    if config.get("schema_version") != 1:
        raise ValueError("unsupported campaign schema")
    if config.get("variants") != ["baseline", "candidate"]:
        raise ValueError("campaign must pair baseline and candidate")
    for key in ("screening_repetitions", "confirmation_repetitions"):
        if not positive_integer(config.get(key)):
            raise ValueError(f"{key} must be a positive integer")
    suites = config["suites"]
    ids = [suite["id"] for suite in suites]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate suite id")
    if selected and selected not in ids:
        raise ValueError(f"unknown suite: {selected}")
    rng = random.Random(config["seed"])
    runs = []
    cells = []
    seen = set()
    for suite in suites:
        if selected and suite["id"] != selected:
            continue
        if not suite.get("required_capabilities"):
            raise ValueError(f'{suite["id"]}: explicit capability gates required')
        count = suite.get("repetitions", config[
            "confirmation_repetitions" if confirmation else "screening_repetitions"])
        if not positive_integer(count):
            raise ValueError("repetitions must be a positive integer")
        factors = suite["factors"]
        if not suite["blocks"] or any(not values for values in factors.values()):
            raise ValueError("empty design")
        suite_cells = []
        for block in suite["blocks"]:
            if set(block).intersection(factors):
                raise ValueError("factor would overwrite a blocking variable")
            for values in itertools.product(*factors.values()):
                parameters = dict(block, **dict(zip(factors, values)))
                if suite["scope"] in ("request", "capacity"):
                    for key in ("prompt_tokens", "generate_tokens", "context_tokens"):
                        if not positive_integer(parameters.get(key)):
                            raise ValueError(f"{key} must be a positive integer")
                    if parameters["prompt_tokens"] + parameters["generate_tokens"] > parameters["context_tokens"]:
                        raise ValueError("prompt plus generation exceeds reserved context")
                identity = json.dumps([suite["id"], parameters], sort_keys=True)
                cell_id = suite["id"] + "-" + hashlib.sha256(identity.encode()).hexdigest()[:12]
                if cell_id in seen:
                    raise ValueError("duplicate experiment cell")
                seen.add(cell_id)
                cell = dict(cell_id=cell_id, suite=suite["id"], phase=suite["phase"],
                            scope=suite["scope"], parameters=parameters,
                            required_capabilities=suite["required_capabilities"],
                            status="not_run", admission="unverified")
                cells.append(cell)
                suite_cells.append(cell)
        # Capacity advances only after each smaller point passes and recovers.
        # Other designs randomize cells independently in each repetition block.
        for repetition in range(count):
            order = list(suite_cells)
            if not suite.get("ordered", False):
                rng.shuffle(order)
            for cell in order:
                variants = list(config["variants"])
                rng.shuffle(variants)
                pair_id = f'{cell["cell_id"]}-r{repetition + 1}'
                for variant in variants:
                    runs.append(dict(pair_id=pair_id, cell_id=cell["cell_id"],
                                     repetition=repetition + 1, variant=variant,
                                     status="not_run"))
    return dict(schema_version=1, execution_enabled=False,
                notice="Specifications only; capability, artifact and memory admission remain required.",
                campaign=config, cells=cells, planned_runs=runs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=ROOT / "bench/integration/campaign.json")
    parser.add_argument("--suite")
    parser.add_argument("--confirmation", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        plan = build_plan(json.loads(args.campaign.read_text()), args.suite, args.confirmation)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n")
    print(f'{len(plan["cells"])} proposed cells; {len(plan["planned_runs"])} paired run entries; no execution')


if __name__ == "__main__":
    main()
