#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT="bench/results/2026-10-19-phase5-coder-layer2-operator-oracle"
MODEL="/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf"
EXPERT="${1:-174}"
RUN_ID="${2:-run1}"
python3 tools/integration/run_control.py \
  --output "$OUT/supervisor-e${EXPERT}-${RUN_ID}" \
  --timeout 900 --interval 1 --sample-clocks -- \
  build/integration/candidate/native_expert_parity "$MODEL" \
  --expert "$EXPERT" \
  --activation-f32 "$OUT/activation-position-511-token-271-layer-2.f32" \
  2
