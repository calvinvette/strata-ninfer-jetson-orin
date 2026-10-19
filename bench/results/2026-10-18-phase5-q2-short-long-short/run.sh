#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
out=${OUTPUT_DIR:-bench/results/2026-10-18-phase5-q2-short-long-short/rerun-$(date +%Y%m%dT%H%M%S)}
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output "$out/supervisor" --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-18-phase5-q2-short-long-short/run_sequence.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/config.json \
  --short-workload bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/workload.json \
  --long-workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/warmup-workload.json \
  --output "$out/result"
python3 bench/results/2026-10-18-phase5-q2-short-long-short/review_sequence.py \
  --result "$out/result/result.json" \
  --supervisor "$out/supervisor/result.json" \
  --samples "$out/supervisor/memory.jsonl" \
  --output "$out/result/independent-review.json"
