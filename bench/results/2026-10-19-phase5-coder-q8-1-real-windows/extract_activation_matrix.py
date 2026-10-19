#!/usr/bin/env python3
"""Extract one exact multi-token activation window from Strata's MoE JSONL capture."""
import argparse
import json
import math
import pathlib
import struct

ap = argparse.ArgumentParser()
ap.add_argument("capture", type=pathlib.Path)
ap.add_argument("output", type=pathlib.Path)
ap.add_argument("--layer", type=int, required=True)
ap.add_argument("--dispatch", type=int, required=True)
ap.add_argument("--width", type=int, required=True)
args = ap.parse_args()
with args.capture.open() as src:
    header = json.loads(next(src))
    matches = [json.loads(line) for line in src if line.strip()]
embd = int(header["n_embd"])
rows = [r for r in matches if r.get("layer") == args.layer and r.get("dispatch") == args.dispatch]
if len(rows) != args.width or any(r.get("n_tok") != args.width for r in rows):
    raise SystemExit(f"expected {args.width} rows from one n_tok={args.width} dispatch; found {len(rows)}")
rows.sort(key=lambda r: int(r["row"]))
if [int(r["row"]) for r in rows] != list(range(args.width)):
    raise SystemExit("captured rows are not a complete ordered token window")
values = [float(x) for row in rows for x in row["activation"]]
if any(len(row["activation"]) != embd for row in rows) or not all(map(math.isfinite, values)):
    raise SystemExit("activation row has wrong width or a non-finite value")
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_bytes(struct.pack("<" + "f" * len(values), *values))
meta = {
    "format": header.get("format"), "layer": args.layer, "dispatch": args.dispatch,
    "n_tok": args.width, "n_embd": embd,
    "rows": [{k: r.get(k) for k in ("row", "stream_row", "token_id", "ids", "route_kind")} for r in rows],
    "activation_file": str(args.output),
}
args.output.with_suffix(args.output.suffix + ".json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta, indent=2))
