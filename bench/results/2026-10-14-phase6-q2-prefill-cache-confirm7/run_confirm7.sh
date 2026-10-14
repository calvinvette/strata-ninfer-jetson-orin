#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-14-phase6-q2-prefill-cache-confirm7
for block in 1 2 3 4 5 6 7; do
  seed=$((2026101600 + block))
  PYTHONPATH=. python3 tools/integration/prefill_cache_screen.py \
    --config bench/results/2026-10-14-phase6-q2-mtp8k-window-screen-final/config-no-adapt.json \
    --workloads bench/results/2026-10-14-phase6-q2-worker-transfer-confirm7/workload/workloads.json \
    --output "$root/block-$(printf '%02d' "$block")" \
    --cache-values 3000 5000 --prefill-values 32 128 \
    --rounds 3 --seed "$seed" --timeout 2400 --no-trace
done
