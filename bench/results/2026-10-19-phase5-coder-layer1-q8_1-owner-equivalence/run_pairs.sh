#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT="${OUTROOT:-bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/paired-runs}"
SEED="${SEED:-20261019}"
BLOCKS="${BLOCKS:-3}"
mkdir -p "$OUT"
if [[ -e "$OUT/order.txt" ]]; then
  echo "refusing to overwrite existing campaign: $OUT" >&2
  exit 2
fi
printf 'seed: %s\nblocks: %s\nselector: iq2_s/q2_0@layer=1\nexpert-cache argument: 3007\n' \
  "$SEED" "$BLOCKS" > "$OUT/order.txt"
for ((block=1; block<=BLOCKS; block++)); do
  mapfile -t arms < <(python3 - "$SEED" "$block" <<'PY'
import random, sys
arms = ["cpu_mirror", "gpu_layer1"]
random.Random((int(sys.argv[1]) << 8) ^ int(sys.argv[2])).shuffle(arms)
print("\n".join(arms))
PY
)
  printf 'block %s order: %s\n' "$block" "${arms[*]}" >> "$OUT/order.txt"
  for arm in "${arms[@]}"; do
    cell="$OUT/block-$block/$arm"
    mkdir -p "$cell"
    cmd=(systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes
         python3 tools/integration/run_control.py
         --output "$cell/supervisor" --timeout 1200 --interval 1 --sample-clocks --
         /home/calvin/.local/python/bin/python3
         bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/run_owner_equivalence.py
         --arm "$arm" --output "$cell/run" --dump-prefill-gdn)
    printf '%q ' "${cmd[@]}" > "$cell/command.txt"
    printf '\n' >> "$cell/command.txt"
    "${cmd[@]}"
  done
done
