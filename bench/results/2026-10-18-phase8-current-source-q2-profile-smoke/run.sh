#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"
output_root=${OUTPUT_ROOT:-bench/results/2026-10-18-phase8-current-source-q2-profile-smoke/rerun-$(date +%Y%m%dT%H%M%S)}

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output "$output_root/supervisor" --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/warmup-workload.json \
  --output "$output_root/run"

python3 bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/review_recall.py \
  --result "$output_root/run/result.json" \
  --workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/workload.json \
  --output "$output_root/run/independent-review.json"
