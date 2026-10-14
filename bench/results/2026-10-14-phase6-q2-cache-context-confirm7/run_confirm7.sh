#!/usr/bin/env bash
set -euo pipefail
block=1
while [ "$block" -le 7 ]; do
  block_name=$(printf '%02d' "$block")
  seed=$((2026101500 + block))
  python3 tools/integration/cache_context_screen.py \
    --config bench/results/2026-10-14-phase6-q2-mtp8k-window-screen-final/config-no-adapt.json \
    --workloads bench/results/2026-10-14-phase6-q2-worker-transfer-confirm7/workload/workloads.json \
    --output "bench/results/2026-10-14-phase6-q2-cache-context-confirm7/block-${block_name}" \
    --cache-values 3000 5000 --context-values 8192 16384 \
    --rounds 3 --seed "$seed" --timeout 2400 --no-trace
  block=$((block + 1))
done
