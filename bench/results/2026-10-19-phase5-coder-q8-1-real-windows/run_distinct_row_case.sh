#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
report="$root/bench/results/2026-10-19-phase5-coder-q8-1-real-windows"
capture="${CAPTURE:-$root/bench/results/2026-10-16-phase5-coder-swap-budget-screen/campaign-retry1/block-2-delayed-control/layer0.jsonl}"
activation="${ACTIVATION:-$report/layer0-dispatch0-nt2-activations.f32}"
model="${MODEL:-$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf}"
binary="${BINARY:-$root/build/integration/candidate/native_expert_parity}"
out="${OUT:-$report/distinct-row-rerun/supervisor}"
python3 "$report/extract_activation_matrix.py" "$capture" "$activation" --layer 0 --dispatch 0 --width 2
mkdir -p "$(dirname "$out")"
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 "$root/tools/integration/run_control.py" --output "$out" --timeout 600 --interval 1 --sample-clocks -- \
  "$binary" "$model" --expert 70 --activation-f32 "$activation" --activation-rows 2 --token-width 2 0
