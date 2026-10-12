#!/usr/bin/env python3
"""Run three randomized scalar/opt-in production-dispatch operator pairs."""
import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN = Path("build/integration/candidate/q8_1_dispatch_bench")
seed_order = random.Random(0x81a11)
seeds = list(range(20261031, 20261038))
orders = []
while len(set(order[0] for order in orders)) < 2:
    orders = []
    for _ in seeds:
        order = ["scalar", "neon"]
        seed_order.shuffle(order)
        orders.append(order)
for pair, (seed, order) in enumerate(zip(seeds, orders), 1):
    result = {}
    for mode in order:
        run = subprocess.run([str(BIN), mode, str(seed)], text=True, capture_output=True)
        (ROOT / f"dispatch-confirm-pair-{pair:02d}-{mode}.txt").write_text(run.stdout)
        (ROOT / f"dispatch-confirm-pair-{pair:02d}-{mode}.stderr.txt").write_text(run.stderr)
        if run.returncode:
            raise SystemExit(f"pair {pair} {mode} failed ({run.returncode})\n{run.stderr}")
        result[mode] = run.stdout
    (ROOT / f"dispatch-confirm-pair-{pair:02d}.json").write_text(json.dumps({
        "pair": pair, "seed": seed, "order": order,
        "scalar_output": result["scalar"], "neon_output": result["neon"],
    }, indent=2) + "\n")
    print(f"paired production-dispatch run {pair}: pass; order={','.join(order)}")
