#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7
block=1
while [ "$block" -le 7 ]; do
  block_name=$(printf '%02d' "$block")
  output="$root/per-cell-scopes/block-${block_name}"
  if [ -e "$output" ]; then
    if [ ! -f "$output/campaign.json" ] || ! python3 - "$output/campaign.json" <<'PY'
import json, sys
from pathlib import Path
campaign = json.loads(Path(sys.argv[1]).read_text())
expected = {f"cache{cache}-ctx{context}" for cache in (1500, 3000) for context in (8192, 16384)}
if ({c.get("name") for c in campaign.get("cells", [])} != expected or
        any(c.get("status") != "pass" for c in campaign.get("cells", []))):
    raise SystemExit(1)
PY
    then
      echo "refusing to overwrite incomplete block ${block_name}: ${output}" >&2
      exit 2
    fi
    echo "block ${block_name} already complete; preserving it"
  else
    seed=$((2026102130 + block))
    python3 tools/integration/cache_context_screen.py \
      --config "$root/config.json" \
      --workloads "$root/workloads.json" \
      --output "$output" \
      --cache-values 1500 3000 --context-values 8192 16384 \
      --rounds 1 --confirmation --seed "$seed" --timeout 1800 \
      --no-trace --sample-clocks --scope-memory-gib 28
  fi
  block=$((block + 1))
done
