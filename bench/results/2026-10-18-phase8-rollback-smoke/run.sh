#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"
pack="$HOME/models/strata-orin-validation/pack"
model_dir="$HOME/models/strata-orin-validation/IQ1_M"
output_root=${OUTPUT_ROOT:-bench/results/2026-10-18-phase8-rollback-smoke/rerun-$(date +%Y%m%dT%H%M%S)}
common=(
  --pack "$pack"
  --native "$model_dir/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf"
  --ple-gguf "$model_dir/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf"
  --expert-profile data/expert-profile-coder.bin
  --expert-cache auto
  --prefill 1
  --spec 4
  --max-context 4096
  --mmap-experts
  --tokens 248045
  --max-new 1
)

for arm in control candidate; do
  systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
    python3 tools/integration/run_control.py \
      --output "$output_root/$arm" \
      --timeout 600 --interval 1 --sample-clocks -- \
      "build/integration/$arm/strata" "${common[@]}"
done
python3 bench/results/2026-10-18-phase8-rollback-smoke/review.py "$output_root"
