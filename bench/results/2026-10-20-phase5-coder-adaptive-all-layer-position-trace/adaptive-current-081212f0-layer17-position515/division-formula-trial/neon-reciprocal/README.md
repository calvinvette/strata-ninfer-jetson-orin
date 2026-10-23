# ARM reciprocal approximation replay — Orin — 2026-10-22

This standalone diagnostic tests whether ARM NEON reciprocal approximation
can reproduce the CUDA `__fdividef` result at the already isolated layer-16,
expert-118 SwiGLU seam. It reads the captured CUDA gate/up rows and CUDA
Q8_1-hidden reference from the sibling `expert118-hidden/` directory. The
captures belong to the pinned Coder IQ1_M model, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and accepted position 515. No model
was loaded for this replay and no Strata runtime code was changed.

`replay_neon_division.cpp` forms the denominator with host `exp`, computes a
NEON reciprocal estimate with zero through three Newton refinements, then
applies separately rounded multiply operations and the CUDA Q8_1 scale, warp
sum, half conversion and rounding contract. It was compiled on Orin with:

```sh
g++ -O3 -std=c++20 -ffp-contract=off -march=armv8-a+simd \
  bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/replay_neon_division.cpp \
  -o /tmp/strata-replay-neon-division
```

The accuracy tradeoff changed which packed field failed, without producing an
exact match. The raw reciprocal estimate differed broadly. One Newton step
matched all 60 CUDA FP16 `d` scales and all quantized codes, but the FP16 `s`
sum differed by one step in blocks 8, 28 and 48. Two or three refinements
matched all `s` values and codes, but `d` differed by one step in blocks 10,
30 and 50. See `results.txt` and
`final-supervisor/supervisor/stdout.txt` for the block-level half encodings.

This rejects a simple NEON reciprocal substitution as a CUDA arithmetic
mirror for this row. It does not test a full ARM implementation of CUDA's
`__fdividef` or `__expf`, prove broad CPU/CUDA error bounds, or resolve the
adaptive accepted-state divergence. The diagnostic ran under the standard
28-GiB supervisor; minimum host/admission availability was 24.46 GiB, cgroup
memory-event counters were zero, clocks were observed dynamically, and EMC
readback was unsupported. Energy was not attributed.
