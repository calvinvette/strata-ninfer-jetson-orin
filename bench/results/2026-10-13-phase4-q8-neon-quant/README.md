# Phase 4 — exact Q8_0 scalar and ARM/NEON quantization comparison

This Orin-only operator experiment compares the explicit Strata scalar Q8_0
oracle path with the ARM implementation in the pinned ggml build. It is useful
for Splash porting as a method and an optimization lead. It is not a Strata
serving result and does not qualify the production Q8_1 activation contract.

## Contract and method

The test feeds the same 256 deterministic, randomized rows of width 2,560 to
both implementations. It checks all 80 Q8_0 blocks in every row, including the
scale, signed quantized values and block sums, before timing. Every process
reports zero byte mismatches. The Strata oracle is selected explicitly with
`expert_set_oracle_q8_0(true)`; the ggml Q8_0 path was built for the Orin's
Cortex-A78AE and its `quantize_row_q8_0` object contains NEON instructions.

Three independent processes used seeds 20261016–20261018. Each process ran nine
randomized-order paired samples; each sample quantized 16 iterations of 256
rows. The runner supervised the campaign with the six-GiB physical-memory
floor and a 28-GiB cgroup cap. No clock controls were used.

## Result

| Metric (per 16 × 256 rows) | Strata scalar oracle | ggml ARM/NEON | Paired delta |
| --- | ---: | ---: | ---: |
| Median of three process medians | 6.297 ms | 0.787 ms | −87.517% |
| Range of process-median paired deltas | — | — | −87.529% to −87.484% |
| Q8_0 byte mismatches | — | — | 0 across all 3 processes |

The supervisor measured 24.57 GiB minimum `MemAvailable` (26,368,724,992 bytes),
above the six-GiB floor. No OOM event was recorded. CPU/GPU clocks were observed
but dynamic; EMC clock access was denied. Energy was not measured. See the raw
clock and memory samples under `supervisor/`.

## Limits and decision

This isolates activation quantization only. It excludes expert dot products,
GPU work, the Q8_1 production route, end-to-end requests, and task quality. Nine
samples within each of three processes do not provide a confidence interval for
independent process variation. No dispatch or default changes follow from this
result. Before using this as a production optimization, qualify the exact Q8_1
rounding/layout contract and measure the complete CPU/GPU expert path under
contention.

## Reproduction and identity

The retained source and scripts are `q8_0_quant_compare.cpp`,
`run_repetitions.py`, and `analyze.py`. The binary and static libraries remain
ignored build artifacts under `build/integration/candidate/`; their SHA256
identities are recorded in `BINARY_SHA256.txt`. The ggml dependency source is
the configure-time checkout at `/tmp/strata-orin-build/_deps/strata_llamacpp-src`.

The binary was built with:

```sh
/usr/bin/c++ -O3 -DNDEBUG -DSTRATA_NATIVE_EXPERTS=1 \
  -DSTRATA_VERSION=\"0.1.41\" -std=c++20 -Iinclude \
  -I/tmp/strata-orin-build/_deps/strata_llamacpp-src/ggml/src/../include \
  bench/results/2026-10-13-phase4-q8-neon-quant/q8_0_quant_compare.cpp \
  build/integration/candidate/libstrata_kernels_cpu.a \
  build/integration/candidate/ggml/src/libggml-cpu.a \
  build/integration/candidate/ggml/src/libggml-base.a -lm \
  -o build/integration/candidate/q8_0_quant_compare
```

Run the three independent processes through the repository's admission and
telemetry guard:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-13-phase4-q8-neon-quant/supervisor \
  --timeout 18000 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-13-phase4-q8-neon-quant/run_repetitions.py
python3 bench/results/2026-10-13-phase4-q8-neon-quant/analyze.py
```

The full per-sample timings are in `analysis.json`; process output and seeds are
in `rep-01..03.txt/json`. This test does not download or use model files.
