#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7
block=1
while [ "$block" -le 7 ]; do
  block_name=$(printf '%02d' "$block")
  seed=$((2026102100 + block))
  python3 tools/integration/cache_context_screen.py \
    --config "$root/config.json" \
    --workloads "$root/workloads.json" \
    --output "$root/per-cell-scopes/block-${block_name}" \
    --cache-values 1500 3000 --context-values 8192 \
    --rounds 3 --seed "$seed" --timeout 1800 \
    --no-trace --sample-clocks --scope-memory-gib 28
  block=$((block + 1))
done
