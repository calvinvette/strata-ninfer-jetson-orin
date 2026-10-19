#!/usr/bin/env bash
set -euo pipefail
MODEL=/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf
ACT=bench/results/2026-10-19-phase5-coder-q8-1-real-windows/layer0-dispatch0-nt2-activations.f32
for expert in 68 119 75 70 188 204 209 180; do
  printf 'expert %s\n' "$expert"
  STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl@layer=0 \
    build/integration/candidate/native_expert_parity "$MODEL" --expert "$expert" \
      --activation-f32 "$ACT" --activation-rows 2 --token-width 2 0
 done
