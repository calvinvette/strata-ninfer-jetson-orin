#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7
output="$root/per-cell-scopes/block-07-replacement"
python3 tools/integration/cache_context_screen.py \
  --config "$root/config.json" \
  --workloads "$root/workloads.json" \
  --output "$output" \
  --cache-values 1500 3000 --context-values 8192 16384 \
  --rounds 1 --confirmation --seed 2026102227 --timeout 1800 \
  --no-trace --sample-clocks --scope-memory-gib 28
