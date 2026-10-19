# Coder Q8_1 verifier-window check on actual weights — Orin — 2026-10-19

This diagnostic extends `native_expert_parity` with an opt-in
`--windows-1-through-8` mode. It loads an actual expert from the pinned Coder
IQ1_M GGUF, uses one captured service activation, and compares the experimental
CPU Q8_1 dot path with CUDA at token widths 1 through 8. The activation is
replicated identically across token lanes. No default inference path changes.

The six cases cover the routed layer 1 experts observed in the short request
(26, 95) and long request (11, 95, 165, 205). All use layer 1, where the expert
tensors are GGML IQ2_S/IQ2_S/Q2_0 for gate/up/down. Each case completed all
8 widths. CPU and CUDA results were bitwise equal at every width (48/48); the
width-invariance check reported zero differing gate/up and down rows in every
case (48/48). All six supervisor records passed with return code 0. Each run
took 2.09–2.12 seconds. Minimum host and admission availability ranged from
24.41 to 24.43 GiB; the 28 GiB scope had no memory events. The supervisor
sampled CPU/GPU clocks; EMC frequency was unavailable to the unprivileged
process, and energy was not measured.

These are operator-level checks on real model tensors and captured activations.
They do not execute a full service request, compare persistent accepted-prefix
state, establish answer quality, measure performance, or explain/fix the
adaptive-residency state divergence. Equal operator outputs therefore do not
close Phase 5. See the exact case logs and supervisor records below.

## Identity and reproducibility

- Hugging Face repository: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`
- Snapshot revision: `5348543e0147355ac9cbcb031184a3546350988e`
- Quantization/path: `Coder-GGUF/IQ1_M`, shard 1 loaded for the selected layer
- Shard SHA256 values: `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` (shard 1) and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` (shard 2)
- Short activation SHA256: `3881ce60e3bf35b6673aeb7a825c75f85b7b31cccff955fca7fe4cf44ef26967`
- Long activation SHA256: `de5315bb9e17f5da8521697d02d5be760b24c4cd8e2b90969ec430466fa26788`
- Diagnostic source SHA256: recorded in `sha256.txt`; CUDA/HIP executable identities are in `build-identities.txt`
- The three focused CTests passed (19.18 seconds total); captured output is in `ctest-supervisor/`.
- Updated diagnostic compiled and linked for CUDA on Orin and HIP on maestro1. The latest HIP rebuild from the matrix-input source completed successfully; its raw output is in `maestro1-hip-distinct-row-build.txt` (370 compiler warnings, no build failure). maestro1 is x86_64 compile evidence only; HIP runtime was not tested. The separate SYCL project does not compile this CUDA/HIP parity utility. maestro1 is x86_64 compile evidence only; the HIP executable was not runtime-tested. The separate SYCL project does not compile this CUDA/HIP parity utility.

Run `./run_real_windows.sh` on Orin to reproduce the six supervised cases. `MODEL`, `BINARY`, and `OUTROOT` may override the defaults. The activation captures are retained in the repository's earlier route-oracle report. The artifact hashes and raw outputs are recorded in `sha256.txt`.

## Distinct rows from a captured two-token dispatch

The initial Q8_1 width sweep replicated one activation row across token lanes.
To exercise grouped rows with different inputs, the diagnostic now also accepts
an exact FP32 activation matrix via `--activation-rows N --token-width N`.
`extract_activation_matrix.py` extracts dispatch 0, rows 0 and 1 from the
retained short-request `strata-moe-dispatch-v2` capture. Both rows route expert
70 to the CPU owner in layer 0, so the expert receives two distinct activations
in one actual grouped dispatch. The activation matrix is 5,120 float32 values;
its SHA256 is recorded in `sha256.txt`.

The supervised native parity check passed. CPU grouped outputs matched the
single-token CPU rows bitwise (`gate/up 0, down 0` differing rows). For the
actual IQ3_XXS gate/up and IQ4_NL down weights, CPU-vs-CUDA relative L1 was
1.52% and all 5,120 output words differed, while both paths remained within
the diagnostic's GGML reference tolerances. This reproduces the expected
activation-contract numerical distinction on a real two-row input; it is not
a persistent-state or answer-quality result. The experimental CPU Q8_1 switch
is limited in `native_expert.cpp` to IQ2_S/Q2_0, so the separate attempted
switch on this IQ3_XXS/IQ4_NL cell is classified unsupported and is not treated
as a Q8_1 arm; the recorded retry leaves the measured default-route values
unchanged. Its first attempt used a misspelled model filename and failed before
loading; both records are retained under `layer0-distinct-row-expert68/cpu-q8_1/`
and `cpu-q8_1-retry/` for traceability. Expert 68 was an exploratory probe;
the grouped-owner claim above is based on expert 70, which appears in both
rows of the captured dispatch.

The focused three CTests passed again on the final CUDA build (20.14 seconds). A post-matrix single-row Q8_1 width regression also passed all 8 widths, preserving the legacy activation input form. Reproduce the matrix extraction and expert-70 probe with `./run_distinct_row_case.sh`; its rerun is in `distinct-row-rerun/supervisor/`. The matrix format probe and raw outputs are retained in `layer0-distinct-row-expert70/` and `matrix-ctest-final/`. The repeated expert-70 supervisor had minimum host/admission availability of 28.20/27.99 GiB over a 1.09-second run, zero cgroup events, dynamic CPU/GPU clock sampling, unavailable EMC readback, and no energy measurement.

## Device-side input correction and route-transition rows

The earlier keyed route report treated the GPU-profile JSONL layer-1 activation
as an upstream input difference. That was a stale host-side capture for rows
where every expert was GPU-owned: the capture hook runs in the CPU dispatch
callback, which may observe a reused host buffer after the graph has advanced.
The verifier's [device-side `ffn_x` dump](../../../src/core/verify.cpp#L1419) records
the actual MoE input inside the graph. The host route hook in
[expert_source.cpp](../../../src/core/expert_source.cpp#L3148) runs in the CPU
dispatch callback; the data suggest that callback can observe a reused host
buffer after the graph advances on all-GPU rows. Reanalysis shows the
device-side layer-1
input is bitwise identical between CPU mirror and GPU-profile arms for all 16
decoded positions. The host route capture repeats the same-position layer-0
input only at all-GPU rows 511 and 513. This corrects the earlier interpretation;
those JSONL values do not establish a changed GPU MoE input.

Combined layer-1 `ffn_y` outputs agree between CPU mirror and GPU profile at
positions 511 and 513. They first differ at position 512, agree again at 513,
then differ at positions 514–526. The exact graph inputs match, so these output
differences are downstream of the same MoE input. This excludes an upstream
activation change for this service pair, but does not by itself identify every
weighted expert contribution.

Eight supervised operator checks used the exact device-captured `ffn_x` rows
for positions 512/token 760 and 514/token 1433 with actual IQ2_S/Q2_0 expert
weights. CPU Q8_1 and CUDA outputs were bitwise equal for all 8/8 tested
expert/row cases:

| Position / token | Expert | Route relation | Default CPU vs Q8_1 relative L1 |
| --- | ---: | --- | ---: |
| 512 / 760 | 95, 11, 205, 18 | CPU mirror-owned; GPU-profile moved to GPU | Q8_1 equals CUDA bitwise |
| 512 / 760 | 90 | CPU-owned in both; GPU-profile uses default CPU mode | 1.367% |
| 514 / 1433 | 30 | CPU-owned in both; GPU-profile uses default CPU mode | 1.561% |
| 514 / 1433 | 159 | CPU-owned in both; GPU-profile uses default CPU mode | 1.686% |
| 514 / 1433 | 182 | CPU-owned in both; GPU-profile uses default CPU mode | 1.632% |

For position 512, the four experts moved from CPU mirror to GPU have exact
Q8_1/CUDA operator parity, while the one expert left on CPU (90) has the
measured default-vs-Q8_1 difference. At position 514 the CPU owner set is the
same in both service arms, but the GPU-profile run uses default CPU math while
the CPU-mirror run opts into Q8_1; all three expert checks show the expected
activation-format difference and Q8_1/CUDA equality. This strongly supports
the CPU activation-format path as the source of these row-level combined-output
differences. The report does not reconstruct the full router-weighted sum, and
positions 515–526 do not have per-row route JSON, so later row-level attribution
remains open.

All 16 supervised operator cases passed in separate 28-GiB scopes, with minimum
host/admission availability 28.08/27.97 GiB, no cgroup memory events, dynamic
CPU/GPU clock sampling, unavailable EMC readback and no energy measurement.
Recompute the layer chain with `python3 analyze_layer_activation_chain.py` and
rerun the exact-device-input expert checks with
`./run_captured_gdn_experts.sh`. The default-vs-Q8_1 per-expert output captures
are reproduced by `./run_default_vs_q8_experts.sh` and summarized with
`python3 analyze_default_vs_q8_outputs.py`; its eight-row result is
`default-vs-q8-output-analysis.json`.
