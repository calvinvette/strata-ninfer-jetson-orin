#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-18-phase6-q2-cache-context-current-source-confirm7
outroot="$root/per-cell-scopes"
block=1
while [ "$block" -le 7 ]; do
  block_name=$(printf '%02d' "$block")
  seed=$((2026101800 + block))
  python3 tools/integration/cache_context_screen.py \
    --config "$root/config.json" \
    --workloads "$root/workloads.json" \
    --output "$outroot/block-${block_name}" \
    --cache-values 3000 5000 --context-values 8192 16384 \
    --rounds 3 --seed "$seed" --timeout 2400 --no-trace --sample-clocks --scope-memory-gib 28
  block=$((block + 1))
done
