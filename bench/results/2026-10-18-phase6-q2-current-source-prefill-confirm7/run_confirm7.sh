#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
out=${1:-/tmp/strata-q2-current-source-prefill-confirm7}
mkdir -p "$out"
cp bench/results/2026-10-18-phase6-q2-current-source-prefill-confirm7/{config.json,workload.json,warmup-workload.json} "$out/"
for block in 1 2 3 4 5 6 7; do
  seed=$((2026101880 + block))
  PYTHONPATH=. python3 tools/integration/prefill_cache_screen.py \
    --config "$out/config.json" --workloads "$out/workload.json" \
    --warmup-workloads "$out/warmup-workload.json" \
    --output "$out/block-$(printf '%02d' "$block")" \
    --cache-values 3000 --prefill-values 32 128 --rounds 1 \
    --confirmation --seed "$seed" --timeout 1800 --no-trace --sample-clocks \
    --cell-memory-max-gib 28
done
python3 bench/results/2026-10-18-phase6-q2-current-source-prefill-confirm7/analyze_confirm7.py --root "$out"
python3 bench/results/2026-10-18-phase6-q2-current-source-prefill-confirm7/plot_confirm7.py --root "$out"
