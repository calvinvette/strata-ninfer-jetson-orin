#!/usr/bin/env python3
"""Summarize a tools/integration/run_control.py memory.jsonl: minimum available and admission RAM, peak swap."""
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1])]
gib = 1024 ** 3
summary = {
    "samples": len(rows),
    "seconds": round(rows[-1]["monotonic_s"] - rows[0]["monotonic_s"], 1),
    "min_available_gib": round(min(r["available_bytes"] for r in rows) / gib, 2),
    "min_admission_available_gib": round(min(r["admission_available_bytes"] for r in rows) / gib, 2),
    "max_swap_used_gib": round(max(r.get("swap_used_bytes", 0) for r in rows) / gib, 2),
}
print(json.dumps(summary, indent=2))
