#!/usr/bin/env bash
set -euo pipefail
root=bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count
for n in 02 03; do
  port=$((18860 + 10#$n))
  systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
    python3 tools/integration/run_control.py \
      --output "$root/supervisor-$n" --timeout 900 --interval 1 --sample-clocks -- \
      python3 "$root/run_vision.py" --config "$root/config.json" \
      --output "$root/run-$n" --fixture "$root/fixture.png" \
      --vision-exe build/integration/vision-cuda/bin/strata-vision \
      --mmproj /home/calvin/models/strata-orin-validation/mmproj-Qwen3.8-Flash-Next-BF16.gguf \
      --port "$port" --vision-min-tokens 16 --vision-max-tokens 16
done
