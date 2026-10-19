#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT="${OUTROOT:-bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/device-route-pair-reproduction}"
mkdir -p "$OUT"
if [[ -e "$OUT/order.txt" ]]; then
  echo "refusing to overwrite existing device-route check: $OUT" >&2
  exit 2
fi
arms=(cpu_mirror gpu_layer1)
python3 - "${SEED:-20261020}" > "$OUT/order.txt" <<'PY'
import random, sys
arms = ["cpu_mirror", "gpu_layer1"]
random.Random(int(sys.argv[1])).shuffle(arms)
print(f"seed: {sys.argv[1]}")
print("order: " + " ".join(arms))
PY
order_line=$(tail -n 1 "$OUT/order.txt")
read -r -a order <<< "${order_line#order: }"
for arm in "${order[@]}"; do
  cell="$OUT/$arm"
  mkdir -p "$cell"
  cmd=(systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes
       python3 tools/integration/run_control.py
       --output "$cell/supervisor" --timeout 1200 --interval 1 --sample-clocks --
       /home/calvin/.local/python/bin/python3
       bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/run_owner_equivalence.py
       --arm "$arm" --output "$cell/run" --dump-prefill-gdn --dump-moe-route-layer 1)
  printf '%q ' "${cmd[@]}" > "$cell/command.txt"
  printf '\n' >> "$cell/command.txt"
  "${cmd[@]}"
done
