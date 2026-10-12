# Phase 4 — Strata-contract Q8_1 NEON candidate

This experiment began as a test-only AArch64 NEON quantizer, then moved the
exact-contract implementation into `act_quant_q8_1` behind the opt-in
`STRATA_Q8_1_NEON=1` environment variable. The default remains the existing
scalar path. The implementation preserves Strata's scale, int8 codes, integer
code sum and `scale * sum` correction.

The candidate uses the same block maximum and scale calculations as the scalar
path, then rounds by adding `+0.5` or `-0.5` before truncation. This preserves
Strata's half-away-from-zero rule; ggml's ARM Q8_1 routine uses nearest-even and
is therefore not a valid byte-identical comparator for this contract.

## Independent contract screen

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

## Integrated dispatch confirmation

After integration, the independent mathematical oracle test passed for both
scalar and opt-in NEON dispatch on 96 full-width inputs at both production
quantization widths (2,560 and 640 values), including zeros, signed half ties,
low scales and randomized values. The focused Orin CTest set passed the Q8_1
scalar/NEON tests, the existing Q8_0 oracle test and `expert_multi_test` (4/4
after the final vector-sum adjustment). After rebuilding the final source, the
artifact-aware Q2_0 `ple_parity` test also passed under the six-GiB supervisor
(24.45 GiB minimum availability).

The current production-dispatch implementation was measured in seven
randomized process pairs. Each arm quantized 16 × 256 rows per sample, with
nine samples per process. The only runtime setting difference was
`STRATA_Q8_1_NEON=1`.

| Metric | Result |
| --- | ---: |
| Median paired quantizer delta | −29.666% |
| Paired bootstrap 95% interval | −29.845% to −29.432% |
| Pair delta range | −30.413% to −29.268% |
| Median scalar / NEON process time | 1.208 ms / 0.850 ms per 16 × 256 rows |

The seven pairs used both arm orders (three scalar-first, four NEON-first).
Per-process samples and the fixed-seed bootstrap are in
`dispatch-analysis.json`. This is operator-only timing; it does not establish
CPU expert, GPU contention or request improvement.

An earlier three-pair integration screen used scalar lane summation and showed
only an 8.9% median reduction; all three pairs happened to run scalar first.
That first implementation's output and supervisor records are retained in
`dispatch-pair-*.txt` and `dispatch-supervisor-v2/`, but are excluded from the
final estimate. Vectorizing the integer sum produced the current implementation
and the seven-pair confirmation.

## Limits and next gate

The Q2_0 API screen is recorded in
`../2026-10-13-phase4-q8_1-neon-q2-api-screen3/README.md`; it measures only the
512/8 workload at 8K context with three independent paired processes. Text
matched in all pairs, while median total request time was effectively tied
(+0.019% paired candidate delta) and prompt time was 0.444% slower. It does not
cover other prompt/context shapes or qualify task quality and CPU/GPU
interaction across contexts. An earlier broader attempt was interrupted before
paired measurements and is retained in
`../2026-10-13-phase4-q8_1-neon-q2-api-confirm7/ABORTED.md`. No default
promotion follows from operator timing alone.

## Reproduction

`q8_1_neon_contract.cpp` preserves the independent screen; `q8_1_dispatch_bench.cpp`
times the production dispatch. `run_repetitions.py` and `analyze.py` reproduce
the initial contract screen; `run_dispatch_pairs.py` and `analyze_dispatch.py`
produce the seven-pair integrated-dispatch evidence. Executables and static
libraries remain local under `build/integration/candidate`; SHA256 identities
are retained in `BINARY_SHA256.txt`.

The Orin API screen uses the Q2_0 GGUF model and native pack under
`~/models/strata-orin-validation/`. The baseline and candidate configs differ
only by `STRATA_Q8_1_NEON=1`. An outer systemd scope caps the campaign at 28 GiB;
each inner `run_control.py` retains the six-GiB physical-memory floor.

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
