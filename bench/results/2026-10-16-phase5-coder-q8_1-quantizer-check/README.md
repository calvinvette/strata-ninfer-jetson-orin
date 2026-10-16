# Coder layer-1 Q8_1 block comparison — Orin — 2026-10-16

This diagnostic compares GGML CPU's actual Q8_1 `from_float` implementation
with Strata's CUDA `native_quantize_q8_1` on two captured 2,560-value layer-1
activations from the Coder IQ1_M swap study. It also checks both producers
against an independent host transcription of the scale, rounded codes, GGML
block sum, and CUDA warp-XOR sum formula. This tests activation blocks only;
it does not execute either expert dot product or measure service behavior.

| Captured input | 32-value blocks | Scale mismatches | Code mismatches | Stored-sum mismatches | Formula failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial short, layer 1 row 10 | 80 | 0 | 0 | 76 | 0 |
| Long request, layer 1 row 0 | 80 | 0 | 0 | 78 | 0 |

For these two inputs, GGML CPU and CUDA produce identical FP16 scale and int8
code bytes. Their stored `s` fields differ by design: GGML stores `d * sum(q)`,
while this CUDA path stores the FP32 input sum before converting it to FP16.
The sampled IQ2_S gate/up and Q2_0 down dot products use the scale and integer
codes; their CUDA formulas do not consume the stored sum. This supports testing
a CPU Q8_1 dot candidate for these symmetric formats, but does not establish
operator parity, accepted-prefix state parity, or a general native-pack
contract. Other weight formats may consume the sum correction and need separate
contracts.

The Q8_1 scalar/NEON `ActQ` tests are a different, engine-specific planar
representation and are not evidence for this check. The CUDA diagnostic target
built locally on Orin, where all 15 existing `native_expert_parity` CTests
passed. The same target compiled and linked with HIP on
maestro1. maestro1 returned status 2 on the no-argument usage path as expected;
it has no qualified accelerator runtime, so the quantizer test was not run
there. Compressed HIP configure/build logs, binary hash, toolchain identity and
usage output are in `hip/`.

The diagnostic source and CUDA binary identities, captured-input hashes,
commands, and raw output are in `results.json` and the adjacent
`*.stdout.txt` files. The model was
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`; shard hashes are included in the
metadata. No model or build artifact is retained here.

Reproduce on Orin1 after building `native_expert_parity`:

```sh
cmake --build build/integration/candidate --target native_expert_parity --parallel 1
build/integration/candidate/native_expert_parity --q8_1-quantizer \
  --activation-f32 bench/results/2026-10-16-phase5-coder-swap-budget-screen/route-oracle-layer1/layer1-row10.f32
build/integration/candidate/native_expert_parity --q8_1-quantizer \
  --activation-f32 bench/results/2026-10-16-phase5-coder-swap-budget-screen/route-oracle-layer1/layer1-long-row0.f32
ctest --test-dir build/integration/candidate \
  -R '^native_expert_parity_iq2_s_q2_0$' --output-on-failure
```
