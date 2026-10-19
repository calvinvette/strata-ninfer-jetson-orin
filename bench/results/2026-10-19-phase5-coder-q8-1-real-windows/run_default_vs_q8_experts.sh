#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
report="$root/bench/results/2026-10-19-phase5-coder-q8-1-real-windows"
model="${MODEL:-$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf}"
binary="${BINARY:-$root/build/integration/candidate/native_expert_parity}"
outroot="${OUTROOT:-$report/default-vs-q8-expert-outputs}"
run_one() {
  local position="$1" token="$2" expert="$3" mode="$4"
  local activation="$report/captured-device-ffnx-experts/position-$position-token-$token.f32"
  local out="$outroot/position-$position-token-$token-expert-$expert/$mode"
  mkdir -p "$out/dumps"
  local -a cmd=("$binary" "$model" --expert "$expert" --activation-f32 "$activation" --activation-rows 1 --token-width 1 --dump-f32-dir "$out/dumps" 1)
  if [[ "$mode" == q8_1 ]]; then
    systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
      python3 "$root/tools/integration/run_control.py" --output "$out/supervisor" --timeout 600 --interval 1 --sample-clocks -- \
      env STRATA_NATIVE_CPU_Q8_1_DOT=1 "${cmd[@]}"
  else
    systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
      python3 "$root/tools/integration/run_control.py" --output "$out/supervisor" --timeout 600 --interval 1 --sample-clocks -- \
      "${cmd[@]}"
  fi
}
for expert in 90; do
  for mode in q8_1 default; do run_one 512 760 "$expert" "$mode"; done
done
for expert in 30 159 182; do
  for mode in q8_1 default; do run_one 514 1433 "$expert" "$mode"; done
done
