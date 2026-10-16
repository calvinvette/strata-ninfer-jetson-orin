# Coder IQ2_S/Q2_0 scalar CPU Q8_1 dot check — Orin — 2026-10-16

An opt-in diagnostic now compares a scalar CPU expert calculation using
GGML's Q8_1 activation quantizer and independently dequantized GGUF weights
against Strata's CUDA grouped expert path. It ran on two captured layer-1
activations for expert 119 from the Coder IQ1_M artifact. Each input is
replicated across the parity utility's three token lanes.

| Captured input | CPU diagnostic vs CUDA relative L1 | Maximum absolute difference | Output words differing bitwise |
| --- | ---: | ---: | ---: |
| Initial short, layer 1 row 10 | 9.334e-4 | 6.101e-5 | 7680 / 7680 |
| Long request, layer 1 row 0 | 6.356e-4 | 4.608e-5 | 7677 / 7680 |

The result is consistent with the earlier activation check: the captured
IQ2_S gate/up and Q2_0 down formats consume Q8_1's scales and integer codes;
the tested codes/scales matched the CUDA producer. The small residual against
CUDA is compatible with different floating-point accumulation order after
GGML weight dequantization. It is not exact route parity.

This is a scalar diagnostic oracle, not a proposed optimized CPU kernel. It
uses float weight dequantization and double accumulation, does not benchmark
latency, and does not inspect accepted-prefix state or full-service behavior.
The normal CPU native route remains on GGML's format-selected Q8_K activation
contract. No production dispatch or default changed. Other native formats and
any Q8_1 sum-correction consumers need their own contracts.

The model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The repo label does not
describe every routed expert tensor: layer 1 uses IQ2_S gate/up and Q2_0 down.
The source shard and activation hashes, Orin source/binary hashes, exact
commands and raw output are in `results.json` and the adjacent stdout files.
No model or build artifact is committed.

The Orin CUDA target rebuilt, both diagnostic invocations exited zero, and all
15 `native_expert_parity_` CUDA CTests passed. The first isolated maestro1 HIP
target attempt reached device linking but `amdgcn-link` terminated with a bus
error. maestro1's root filesystem had no free space, so the retry moved build
temporaries to `/mnt/sda2` and linked the target; its no-argument usage path
returned the expected status 2 after setting the pinned ROCm library path. Both
attempt logs are retained as compressed text under `hip/`; the initial missing
library loader output is retained separately. This is compile/CLI evidence
only, not accelerator execution.

Reproduce on Orin1 after building `native_expert_parity`:

```sh
cmake --build build/integration/candidate --target native_expert_parity --parallel 1
STRATA_DIAG_CPU_Q8_1_DOT=1 build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 119 --activation-f32 \
  bench/results/2026-10-16-phase5-coder-swap-budget-screen/route-oracle-layer1/layer1-row10.f32 1
STRATA_DIAG_CPU_Q8_1_DOT=1 build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 119 --activation-f32 \
  bench/results/2026-10-16-phase5-coder-swap-budget-screen/route-oracle-layer1/layer1-long-row0.f32 1
```
