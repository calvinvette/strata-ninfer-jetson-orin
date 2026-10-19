#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
report="$root/bench/results/2026-10-19-phase5-coder-q8-1-real-windows"
model="${MODEL:-$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf}"
binary="${BINARY:-$root/build/integration/candidate/native_expert_parity}"
outroot="${OUTROOT:-$report/captured-device-ffnx-experts}"
mkdir -p "$outroot"
run_one() {
  local position="$1" token="$2" expert="$3" activation="$outroot/position-$1-token-$2.f32" out="$outroot/position-$1-token-$2-expert-$3/supervisor"
  if [[ ! -f "$activation" ]]; then
    python3 "$report/extract_gdn_ffn_x.py" "$activation" --position "$position" --token "$token"
  fi
  systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
    python3 "$root/tools/integration/run_control.py" --output "$out" --timeout 600 --interval 1 --sample-clocks -- \
    env STRATA_NATIVE_CPU_Q8_1_DOT=1 "$binary" "$model" --expert "$expert" \
    --activation-f32 "$activation" --activation-rows 1 --token-width 1 1
}
# At position 512, mirror routes these five experts to CPU; four move to GPU in gpu_layer1.
for expert in 95 11 205 18 90; do run_one 512 760 "$expert"; done
# At position 514, these three experts remain CPU-owned in both profiles, but CPU mode differs.
for expert in 30 159 182; do run_one 514 1433 "$expert"; done
