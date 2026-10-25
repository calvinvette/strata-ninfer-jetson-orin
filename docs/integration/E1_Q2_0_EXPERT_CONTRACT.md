# E1 Q2_0 routed expert contract

Status: contract and codec oracle defined; CUDA adapter not implemented yet.
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
small-token organization only. Their codecs and reduction implementation are
not the Q2_0 oracle. Any promoted code must carry Apache-2.0 notices and a
function-level provenance note.

## E1 limits and next decision

This document and synthetic oracle establish the first codec/geometry contract,
not real-payload CUDA parity, slot lifetime correctness, or NInfer integration.
Next: add a small caller-owned CUDA adapter for one-token Q2_0 resident work,
first compare decoded rows and projection outputs against this oracle and an
independent ggml-linked decoder, then wire the opt-in selector. Do not start
staging absent experts until E2 proves the resident path.
