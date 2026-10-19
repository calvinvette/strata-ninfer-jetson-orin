#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
model="${MODEL:-$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf}"
binary="${BINARY:-$root/build/integration/candidate/native_expert_parity}"
activations="$root/bench/results/2026-10-16-phase5-coder-swap-budget-screen/route-oracle-layer1"
outroot="${OUTROOT:-$root/bench/results/2026-10-19-phase5-coder-q8-1-real-windows/rerun}"
run_one() {
  local name="$1" expert="$2" activation="$3"
  mkdir -p "$outroot/$name"
  systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
    python3 "$root/tools/integration/run_control.py" \
    --output "$outroot/$name/supervisor" --timeout 600 --interval 1 --sample-clocks -- \
    env STRATA_NATIVE_CPU_Q8_1_DOT=1 "$binary" "$model" \
    --expert "$expert" --activation-f32 "$activations/$activation" \
    --windows-1-through-8 1
}
run_one short-layer1-expert26 26 layer1-row10.f32
run_one short-layer1-expert95 95 layer1-row10.f32
run_one long-layer1-expert11 11 layer1-long-row0.f32
run_one long-layer1-expert95 95 layer1-long-row0.f32
run_one long-layer1-expert165 165 layer1-long-row0.f32
run_one long-layer1-expert205 205 layer1-long-row0.f32
