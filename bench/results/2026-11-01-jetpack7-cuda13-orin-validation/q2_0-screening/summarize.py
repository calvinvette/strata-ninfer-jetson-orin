import json, statistics, sys
from pathlib import Path
for cell in sys.argv[1:]:
    rows = [json.loads(p.read_text()) for p in sorted(Path(cell).glob("matched-*.json"))]
    print(Path(cell).name, "rows", len(rows), "statuses", sorted({r["status"] for r in rows}))
    for rep in (32, 128, 256):
        rs = [r for r in rows if r["repeat"] == rep]
        if not rs: continue
        med = lambda k: statistics.median(r[k] for r in rs if r[k] is not None)
        print(f"  {rs[0]['prompt_tokens']}-token prompt (n={len(rs)}): PP {med('prompt_tok_s'):.1f} / TG {med('decode_tok_s'):.1f} / TTFT {med('client_ttft_s'):.1f} s"
              f"  | TG range {min(r['decode_tok_s'] for r in rs):.1f}-{max(r['decode_tok_s'] for r in rs):.1f}")
