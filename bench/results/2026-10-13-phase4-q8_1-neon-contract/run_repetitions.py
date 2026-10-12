#!/usr/bin/env python3
"""Run three independent exact-contract Q8_1 scalar/NEON comparisons."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN = Path("build/integration/candidate/q8_1_neon_contract")
for rep, seed in enumerate((20261016, 20261017, 20261018), 1):
    result = subprocess.run([str(BIN), str(seed)], text=True, capture_output=True)
    (ROOT / f"rep-{rep:02d}.txt").write_text(result.stdout)
    (ROOT / f"rep-{rep:02d}.stderr.txt").write_text(result.stderr)
    (ROOT / f"rep-{rep:02d}.json").write_text(json.dumps({
        "seed": seed, "returncode": result.returncode,
    }, indent=2) + "\n")
    print(f"rep-{rep}: {'passed' if result.returncode == 0 else 'failed'} seed={seed}")
    if result.returncode:
        raise SystemExit(result.returncode)
