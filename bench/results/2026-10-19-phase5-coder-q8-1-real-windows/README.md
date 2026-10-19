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
- Diagnostic source SHA256: recorded in `sha256.txt`
- The three focused CTests passed (19.18 seconds total); captured output is in `ctest-supervisor/`.
- Updated diagnostic compiled and linked for CUDA on Orin and HIP on maestro1. Raw HIP build output is in `maestro1-hip-build.txt`; the target emitted compiler warnings but completed successfully. maestro1 is x86_64 compile evidence only; the HIP executable was not runtime-tested. The separate SYCL project does not compile this CUDA/HIP parity utility.

Run `./run_real_windows.sh` on Orin to reproduce the six supervised cases. `MODEL`, `BINARY`, and `OUTROOT` may override the defaults. The activation captures are retained in the repository's earlier route-oracle report. The artifact hashes and raw outputs are recorded in `sha256.txt`.
