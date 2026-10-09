#!/usr/bin/env python3
"""Verify copied source and historical evidence against the pinned import manifest."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    manifest = json.loads((ROOT / "reference/ninfer-import.json").read_text())
    failures = []
    seen = set()
    for record in manifest["files"]:
        name = record["path"]
        path = (ROOT / name).resolve()
        if name in seen or not path.is_relative_to(ROOT):
            failures.append(f"invalid/duplicate path: {name}")
            continue
        seen.add(name)
        if not path.is_file():
            failures.append(f"missing: {name}")
            continue
        data = path.read_bytes()
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            failures.append(f"changed: {name}")
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        return 1
    print(f'Verified {len(seen)} imports from {manifest["source_commit"]} and labeled local evidence')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
