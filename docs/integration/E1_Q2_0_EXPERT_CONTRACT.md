# E1 Q2_0 routed expert contract

Status: **E1 contract complete (2026-10-25)**. The bounded CUDA prototype and
service integration are recorded under E2/E3; see the current implementation
limits and E4 coverage report below.
Inventory source: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, local Q2_0 shards under
`~/models/strata-orin-validation/Q2_0/`. The inventory JSON is generated locally
with `tools/integration/inventory_tensors.py`; model data is not stored here.

## Exact model contract

The two-shard GGUF has 1,223 tensors in shard 1 and one tensor in shard 2. Across
48 decoder layers, each routed gate, up, and down tensor is Q2_0:

| Tensor | GGUF shape, fastest dimension first | Logical view |
| --- | --- | --- |
| `blk.L.ffn_gate_exps.weight` | `[2560, 640, 512]` | 512 experts × 640 rows × 2560 inputs |
| `blk.L.ffn_up_exps.weight` | `[2560, 640, 512]` | 512 experts × 640 rows × 2560 inputs |
| `blk.L.ffn_down_exps.weight` | `[640, 2560, 512]` | 512 experts × 2560 rows × 640 inputs |

The router selects 10 experts from 512, and the model's routed operation is
gate/up projection, SwiGLU, then down projection. Strata retains routing, route
weight application, shared-expert work, residual/mixer behavior, cache ownership,
and output publication. The adapter computes one *unweighted* 2560-element output
for each selected token/expert pair. It does not add a residual or shared expert.

For a GGUF Q2_0 block, 64 weights occupy 18 bytes: little-endian FP16 scale `d`
followed by 16 packed bytes. Weight `j` uses the two-bit code at
`qs[j//4] >> (2*(j%4))`; codes 0,1,2,3 represent -1,0,1,2, so
`w[j] = (code - 1) * fp16_to_fp32(d)`. Rows are contiguous, with 40 blocks per
gate/up row and 10 blocks per down row. These dimensions and the 64-value block
are confirmed against the actual GGUF tensor offsets and Strata's existing
Q2_0 contract; do not substitute the historical 128-value Q2_0 layout.

## Independent oracle

`tools/integration/test_q2_0_expert_oracle.py` is a dependency-free scalar oracle
and synthetic fixture check. It decodes each value directly from bytes, then
computes gate and up dot products, `silu(gate) * up`, and down dot products in
Python float64. It checks every 2-bit code, block/row boundaries, half-scale
decoding, and the real 2560/640 projection dimensions. This is an independent
mathematical reference, not a claim of parity with ggml or a CUDA kernel. E2 must
compare it with a separately linked trusted Q2_0 decoder and define numerical
bounds before performance screening.

For a real-payload spot check, the first 64 blocks of eight Q2_0 tensors in shard
1 were decoded by the Python byte-level oracle and the linked
`dequantize_row_q2_0` from llama.cpp/ggml commit
`3cf03257f219afbe7334045ff7c6a06ac68c627d`. All 32,768 decoded FP32 values
matched bit-for-bit; all eight sum and absolute-sum checksums matched. For
`blk.0.ffn_down_exps.weight`, the checksums were `sum=0.6449966431` and
`sumabs=33.21868134`. Strata's C++ utility also checked eight Q2_0 tensors ×
their first 64 blocks against the structural code/scale invariant with zero
violations. This qualifies sampled codec decoding only; full tensor payloads
were not exhaustively decoded in this check.

The reusable `tools/integration/q2_0_expert_oracle.py` was also run on actual
layer-0, expert-32 gate/up/down rows from the Q2_0 artifact. Its input was the
previously captured layer-0 activation for expert 32 from the related Coder IQ1_M
artifact (`2026-10-15-phase5-activation-error-decomposition`, SHA256
`607553ddddee20523c8259ba171eedc35fb01239dca19d1124114cf574515391`). This is
a real activation vector but a cross-variant input, not an activation captured
from the Q2_0 model. Under exact Q2_0 decoding and FP64 dots/SiLU the unweighted
output SHA256 is
`86630939911b8899265cc806fefc448ce462f32958c13a150af84936fc604c9a`, max
absolute value `0.08953284`, RMS `0.01652383`. The JSON includes gate/up/hidden
range checks. This establishes a repeatable oracle fixture for real weights and
a representative activation; it does not validate a runtime kernel or the
Q2_0 model's own activation distribution.

The same `(layer 0, expert 32)` case was then run through the current Strata
`native_expert_parity` CUDA executable using that activation. CUDA weight
dequantization matched ggml for all 4,915,200 values bit-for-bit, and the harness
reported no failures. Comparing the scalar oracle output to the harness's
unquantized float output gave relative L1 `3.76e-8`, max absolute difference
`4.31e-9`, and RMS difference `6.35e-10`. The current quantized-activation CPU
and GPU expert outputs were each about 1.2023% relative L1 from that reference;
the CPU/GPU pair differed by `1.04e-7` relative L1. This qualifies the
independent reference and the existing Strata Q2_0 route for this one real-weight,
cross-variant activation case. At the E1 checkpoint this did not qualify an
NInfer-derived kernel; the later E2/E3/E4 evidence is summarized below.
Reproduction uses `native_expert_parity` with `--expert 32`, the activation path
above, and layer `0`, plus `q2_0_expert_oracle.py --output-f64 <path>`; raw output
and model-derived tensors remain outside Git.

Expected execution arithmetic: input activations are the represented values
delivered to the adapter; decoded Q2_0 weights are exact in binary16 scale and
integer code, but dot-product accumulation order is implementation-defined.
The reference uses FP64 accumulation and FP64 SiLU. The public output contract
will be set in E2 after comparison with Strata's established path and independent
reference. Route weights are applied by Strata after this adapter returns.

## Lifetime and dispatch rules

- Caller owns weight pointers, activation/output storage, descriptors, workspace,
  and stream. No allocation or host synchronization is allowed during invocation.
- Weight/cache-slot references stay valid until the work is complete on the
  supplied stream. Slot reuse must be guarded by generation/lifetime tracking.
- Duplicate `(token, expert)` work is preserved unless Strata explicitly
  canonicalizes it before dispatch; output row mapping is explicit and stable.
- Empty jobs are a no-op. Partial batches are valid. A zero resident set does not
  imply success in strict backend mode; it is a reported unsupported/fallback
  condition. Ordinary mode may retain Strata fallback.
- Graph replay requires stable descriptor/workspace addresses and admitted
  capacities. The adapter cannot retain state across invocations.
- Unsupported codecs, invalid geometry, stale slots, capacity overflow, or an
  unsupported backend must be rejected before launch in strict mode.

## NInfer source disposition

The pinned reference is `reference/ninfer/` at planning revision
`b07248f2528125aeda7550055580204541f1714c`, Apache-2.0. Its complete
`ninfer::ops::sparse_moe` contract is incompatible: hidden 2048, intermediate
512, top-8, BF16 activations, fixed Q4/Q5/Q6/W8 weight profiles, and integrated
router/shared merge/residual epilogue. Do not call that wrapper for this model.
The decode internals under
`reference/ninfer/src/ops/sparse_moe/decode/` are candidates for schedule and
small-token organization only. More specifically, `dot_two_rows` and
`sparse_moe_d3_path_tiled_kernel` in
`reference/ninfer/src/ops/sparse_moe/decode/sparse_moe_decode_kernels.cu` are
gate/up + SiLU candidates; their `Q4Codec`/`W8Codec` decoders and 2048/512
dimensions must be replaced. `dot_fp32_rows` and
`sparse_moe_d4_token_kernel` are down-projection candidates; the latter also
applies route weights, computes the shared path and adds the residual, all of
which must be removed from the expert-only adapter. The `launch_d3_small_t_codec`
and `launch_d4_small_t_codec` helpers show small-token row scheduling, not a
compatible Q2_0 dispatch contract. Their codecs and reduction implementation
are not the Q2_0 oracle. Any promoted code must carry Apache-2.0 notices and a
function-level provenance note.

## E1 limits and next decision

This document and oracle establish the first codec/geometry contract and a
real-weight numerical fixture, not Q2_0-model-native activation coverage. E2/E3
added and measured an opt-in caller-owned CUDA adapter, strict selector, and
bounded staged/direct-mapped paths; see the [E2 report](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/README.md)
and [E3 reports](../../bench/results/2026-10-25-phase-e2-q2-ninfer-resident-smoke/staged-screen/README.md).
Real-weight FP64 parity and grouped route parity pass for the recorded fixture.
The adapter remains Q2_0/Q2_0 only. E4's grouped operator checks cover 3, 64 and
128 tokens, but do not qualify end-to-end serving performance at the 64/128
prefill chunks. The Coder IQ1_M and original IQ3_S variants have mixed expert
codecs and are not covered by this adapter.
These are implementation and capability boundaries, not performance claims.
