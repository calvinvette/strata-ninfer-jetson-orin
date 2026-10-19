#!/usr/bin/env bash
set -euo pipefail
root="${OUTROOT:-bench/results/2026-10-18-phase5-coder-layer1-route-isolation/all-16-positions-three-arm-reproduction}"
seed="${SEED:-20261000}"
mkdir -p "$(dirname "$root")"
mkdir "$root"
mapfile -t order < <(python3 - "$seed" <<'PY'
import random, sys
arms = ["cpu_default", "cpu_mirror", "gpu_layer1"]
random.Random(int(sys.argv[1])).shuffle(arms)
print("\n".join(arms))
PY
)
printf 'seed: %s\nrandomized order: %s\n' "$seed" "${order[*]}" > "$root/order.txt"
for arm in "${order[@]}"; do
  mkdir "$root/$arm"
  cmd=(systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes
       python3 tools/integration/run_control.py
       --output "$root/$arm/supervisor" --timeout 1200 --interval 1 --sample-clocks --
       /home/calvin/.local/python/bin/python3
       bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_all16.py
       --arm "$arm" --output "$root/$arm/result")
  printf '%q ' "${cmd[@]}" > "$root/$arm/command.txt"
  printf '\n' >> "$root/$arm/command.txt"
  "${cmd[@]}"
done
