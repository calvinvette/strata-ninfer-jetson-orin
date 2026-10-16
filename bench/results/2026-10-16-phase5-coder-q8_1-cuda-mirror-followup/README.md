# Coder CPU Q8_1 CUDA-row mirror and recovery screen — Orin — 2026-10-16

This experiment implemented an opt-in CPU mirror of CUDA's packed integer row
arithmetic for the IQ2_S gate/up and Q2_0 down expert pair. The model was the
IQ1_M snapshot from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, in
`~/models/strata-orin-validation/`. The Coder GGUF's repository label is not
the routed tensor type: layer 1 expert 119 uses IQ2_S gate/up and Q2_0 down.
No model or build product is committed.

`STRATA_NATIVE_CPU_Q8_1_DOT=1` selects the mirror only for that exact format
pair. It preserves the CUDA integer accumulation, scale combination and
warp-lane reduction order. The normal CPU activation route and default dispatch
are unchanged. The tested service binary SHA256 is recorded in `inputs.json`;
it was built from the `c62f3c90` tree with the experiment source change still
uncommitted.

## Operator checks

The opt-in synthetic IQ2_S/Q2_0 parity test passed and now requires bitwise CPU
versus CUDA equality. All 16 `native_expert_parity_` CUDA CTests passed. A real
captured layer-1 expert-119 activation also produced bitwise-equal CPU and CUDA
outputs (0 of 7,680 words differed). Both outputs were within 1.20e-2 relative
L1 of the independent GGML dequantize-and-double-accumulate oracle, inside the
parity utility's 3.0e-2 bound. The output is retained under `parity/`. This
validates the operator seam, not full request state or model quality.

## Randomized recovery screen

Three same-day blocks randomized the default GGML CPU route and the CUDA-row
mirror route. Each supervised arm used the same Coder IQ1_M binary and profile,
MTP off, FP16 KV, zero prompt cache, cadence-4 accepted-only adaptation with an
8-swap budget, and a short-512 / long-2048 / short-512 recovery / identical
short continuation sequence. Each request generated 16 tokens. Route tracing
was enabled, so this is state and correctness evidence, not a timing test.

| Block | Order | Default continuation tokens differing from initial | Mirror continuation tokens differing from initial | Min host availability | Min admission availability |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | Default, mirror | 0/16 | 13/16 | 14.22 GiB | 14.22 GiB |
| 1 | Mirror, default | 0/16 | 13/16 | 14.49 GiB | 10.39 GiB |
| 2 | Mirror, default | 0/16 | 13/16 | 14.44 GiB | 9.35 GiB |

All six arms returned the same 16 recovery tokens as their own initial short
request. Each arm passed all 15 adaptive byte checks and all 15 residency
checks. The initial-to-recovery state fingerprint changed in the same five
fields in every arm: `gdn`, `tail`, `pooled`, `pooled_full` and `kv`. The
following identical short request matched the initial answer in all three
default arms, but differed at 13 positions in all three mirror arms. This
screen therefore rejects the mirror as a fix for the observed adaptive-route
continuation drift. It does not establish why the full service diverges, nor
does it qualify a speed or quality improvement.

The six runs produced 1,264 one-second memory samples. Minimum physical host
availability was 14.22 GiB and minimum admission availability was 9.35 GiB;
both stayed above the six-GiB reserve. Cgroup `high`, `max`, `oom` and
`oom_kill` counters remained zero. The supervisor used
`MemoryMax=28G`; clocks were sampled read-only and energy was not attributed to
individual requests. Raw requests, state hashes, route traces, service logs,
clock samples and supervisor records are retained in `screen3/`.

The earlier single diagnostic pair is retained in `exact-active-retry/` and
`default-active/`. The first candidate attempt in `exact-active/` completed its
first request but exposed a stale hash parser in the harness; it was not used
for conclusions. The corrected parser reads current `ACCEPTED_PREFIX` state
records. `run_recovery_screen.py` reproduces the randomized three-block screen.

## Backend checks

Orin CUDA built `strata` and `native_expert_parity`; the 16 parity CTests and
the captured activation test passed. On maestro1, one-job HIP builds of
`strata` and `native_expert_parity` and a one-job SYCL `strata` build passed,
and both service `--help` checks passed. The build snapshot started from
`4b72a72b`; all CMake, include and source files changed through `c62f3c90` were
overlaid, together with the current experimental source edits. Their hashes,
build logs and binary hashes are in `backend-maestro1/`. The original remote
Phase 8 source snapshot was restored after the checks. maestro1 results are
compile/link and CLI evidence only; no HIP or SYCL device ran this model.

## Reproduction

From the repository root, run the randomized screen with the bounded supervisor:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 bench/results/2026-10-16-phase5-coder-q8_1-cuda-mirror-followup/run_recovery_screen.py \
  --blocks 3 --seed 20261019 \
  --output bench/results/2026-10-16-phase5-coder-q8_1-cuda-mirror-followup/screen3
```

The source in this record is an opt-in diagnostic. Phase 5 remains open; this
result does not close state transaction, graph lifetime or broader model/KV
qualification gates.
