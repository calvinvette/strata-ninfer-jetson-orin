#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-17-phase6-q2-prefill-long-workload-current-source
output_root=${1:-"$root"}
for block in 1 2 3 4 5 6 7; do
  seed=$((2026101720 + block))
  PYTHONPATH=. python3 tools/integration/prefill_cache_screen.py \
    --config "$root/config.json" --workloads "$root/workload.json" \
    --warmup-workloads "$root/warmup-workload.json" \
    --output "$output_root/block-$(printf '%02d' "$block")" \
    --cache-values 3000 --prefill-values 32 128 --rounds 1 --confirmation \
    --seed "$seed" --timeout 2400 --no-trace --sample-clocks \
    --cell-memory-max-gib 28
done
