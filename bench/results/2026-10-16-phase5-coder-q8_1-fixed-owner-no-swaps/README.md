# Coder IQ1_M CPU-route comparison with adaptation disabled — Orin — 2026-10-16

This randomized supervised pair tests whether the route arithmetic difference
persists with adaptive swaps disabled. Both arms used
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`, its IQ1_M shards, the same
current-source binary and cache profile, MTP2, prompt-cache capacity 0, and
the same short/long/short/continuation sequence. Both used
`--adapt-every 0 --adapt-swaps 0`; `--adapt-accepted-only` was absent. The
mirror ran first, followed by default. This is correctness evidence, not a
timing comparison.

At dispatch 1393/layer 1, the captured activations, expert IDs and owners
matched. All four CPU-owned experts (209, 207, 85, 153) differed in all 2,560
output values between the default CPU route and the CUDA Q8_1 mirror. At the
next layer dispatch (1394/layer 2), the activation first differed while expert
IDs and owners still matched. Across the 192 captured route rows, the first
expert-ID and owner differences appeared later at dispatch 1400/layer 8, after
activation drift had begun. Adaptive swaps were off; the later owner changes
followed different router selections against the same static cache profile.

The verifier's layer-1 `STGDIAG4` combined output capture contained 64 rows per
arm. Of 62 rows with matching position and input token, no `ffn_y` output was
bitwise equal. The first shared row, position 511/token 271, differed in all
2,560 values (maximum absolute delta `2.1168e-4`, relative L1 `0.0040171`).
The route trace and verifier capture do not yet provide a direct event-key join
from dispatch 1393 to a particular `ffn_y` row; the report therefore treats
the route-row and combined-output captures as separate observations in the
same service pair.

Both arms returned identical 16-token initial and recovery short responses.
The long response differed at 3/16 token positions. The subsequent short
continuation matched at all 16 positions across arms. Within each route, the
initial and recovery responses had identical token IDs and persistent-state
fingerprints. Across routes, persistent-state fingerprints differed after
each request. This shows a route-dependent numeric/state difference without
adaptive swaps; it does not show that the mirror preserves Strata's default
numerics or improves task quality.

Both supervised arms passed. Minimum host/admission availability was 14.465
GiB for default and 14.460 GiB for the mirror across 223 and 197 one-second
samples. Cgroup low/high/max/OOM counters remained zero, above the six-GiB
floor. Energy was not attributed; EMC clock sampling was unsupported because
the Tegra debugfs clock path denied access. No performance claim follows.

The model shard hashes are `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad`
and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
Both arms used binary SHA256
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`.

Reproduce the run and analysis with:

```sh
/usr/bin/python3.10 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/run_trace_pair.py \
  --seed 20261028 --adapt-every 0 --adapt-swaps 0 \
  --capture-cpu-outputs --capture-combined-moe \
  --output bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/reproduction

python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/analyze_combined_moe.py \
  bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/reproduction/default/result/combined-moe.bin \
  bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/reproduction/cuda_mirror/result/combined-moe.bin \
  --default-service bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/reproduction/default/result \
  --mirror-service bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/reproduction/cuda_mirror/result \
  --output bench/results/2026-10-16-phase5-coder-q8_1-fixed-owner-no-swaps/reproduction/combined-output-analysis.json
```

Phase 5 remains open. The mirror remains an opt-in diagnostic only.
`SHA256SUMS.txt` verifies the retained captures, logs, request outputs and
supervisor telemetry.
