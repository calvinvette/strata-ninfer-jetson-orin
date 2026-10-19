#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BASE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?pass a new output directory}"

run_arm() {
    local name="$1" every="$2" swaps="$3" optin="$4"
  local -a prefix=() route_args=()
  if [[ "$optin" == yes ]]; then
    local selector="${Q8_1_SELECTOR:-all}"
    prefix=(env "STRATA_NATIVE_CPU_Q8_1_DOT=$selector")
    route_args=(--cpu-q8-1-pair "$selector")
  fi
  systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
    "${prefix[@]}" python3 tools/integration/run_control.py \
      --output "$OUT/$name/supervisor" --timeout 1200 --interval 1 --sample-clocks -- \
      python3 "$BASE/run_service.py" --adapt-every "$every" --adapt-swaps "$swaps" \
        --continuations 1 --prompt-cache 0 "${route_args[@]}" \
        --output "$OUT/$name/run"
}

# Adaptive migration first, then the fixed-residency pair. Keep all four arms serial.
run_arm control-v2 4 8 no
run_arm mirror 4 8 yes
run_arm fixed-control 0 0 no
run_arm fixed-mirror 0 0 yes
