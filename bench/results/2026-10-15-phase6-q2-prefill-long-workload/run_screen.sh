#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-15-phase6-q2-prefill-long-workload
output=${1:-"$root/screen"}
PYTHONPATH=. python3 tools/integration/prefill_cache_screen.py \
  --config "$root/config.json" --workloads "$root/workload.json" \
  --output "$output" --cache-values 3000 --prefill-values 32 128 \
  --rounds 1 --confirmation --seed 2026101526 --timeout 2400 --no-trace --sample-clocks
