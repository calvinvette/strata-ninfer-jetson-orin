# Phase 4 — Strata-contract Q8_1 NEON quantizer screen

This test-only AArch64 NEON quantizer implements Strata's current Q8_1 contract
and compares it with `act_quant_q8_1` on Orin. It preserves Strata's separate
scale, int8 codes, integer code sum and `scale * sum` correction. It is an
optimization screen, not a production change or request-level result.

The candidate uses the same block maximum and scale calculations as the scalar
path, then rounds by adding `+0.5` or `-0.5` before truncation. This preserves
Strata's half-away-from-zero rule; ggml's ARM Q8_1 routine uses nearest-even and
is therefore not a valid byte-identical comparator for this contract.

## Method and results

Each process checked 256 rows × 2,560 values (20,480 Q8_1 blocks), including a
zero row, deliberate positive and negative half-tie values, and randomized
finite values. It compared scale, quantized bytes, integer sums and correction
values exactly. Three independent processes reported zero mismatched blocks.
Each process then ran nine randomized-order paired samples, each quantizing 16
iterations of 256 rows.

| Median per 16 × 256 rows | Scalar Strata Q8_1 | Test-only NEON Q8_1 | NEON delta |
| --- | ---: | ---: | ---: |
| Median of three process medians | 1.211 ms | 0.841 ms | −30.550% |
| Process-median delta range | — | — | −30.554% to −30.407% |
| Mismatched blocks | — | — | 0 of 20,480 per process |

The supervised run's minimum host `MemAvailable` was 26,369,216,512 bytes
(24.57 GiB), above the six-GiB floor. No OOM event was recorded. Clocks remained
dynamic; EMC frequency access was denied. Energy was not measured. No clock
controls were used.

## Limits and next gate

This is quantization-only timing. It excludes expert dot work, CPU/GPU
contention, request latency and task quality. Three processes are a screening
sample, not a confidence interval. Production dispatch and default behavior are
unchanged. The measured operator result warrants integrating the same algorithm
behind an opt-in path, followed by exact-contract tests, CPU expert contention
checks and held-out request comparisons before considering promotion.

## Reproduction

`q8_1_neon_contract.cpp` is the test-only candidate; `run_repetitions.py` records
the three process outputs; `analyze.py` validates and summarizes them. The
executable and static libraries remain local under `build/integration/candidate`
and their SHA256 values are retained in `BINARY_SHA256.txt`.

Build and run on AArch64:

```sh
/usr/bin/c++ -O3 -DNDEBUG -std=c++20 -march=armv8.2-a+simd -Iinclude \
  bench/results/2026-10-13-phase4-q8_1-neon-contract/q8_1_neon_contract.cpp \
  build/integration/candidate/libstrata_kernels_cpu.a \
  build/integration/candidate/ggml/src/libggml-cpu.a \
  build/integration/candidate/ggml/src/libggml-base.a -lm \
  -o build/integration/candidate/q8_1_neon_contract
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-13-phase4-q8_1-neon-contract/supervisor \
  --timeout 18000 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-13-phase4-q8_1-neon-contract/run_repetitions.py
python3 bench/results/2026-10-13-phase4-q8_1-neon-contract/analyze.py
```
