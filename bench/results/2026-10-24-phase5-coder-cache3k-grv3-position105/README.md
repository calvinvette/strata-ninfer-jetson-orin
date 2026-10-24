# Coder cache-3k GR-V3 state-drift diagnostics

Date: 2026-10-24. Device: Jetson AGX Orin, CUDA 12.6. Model: Coder
IQ1_M, `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. This is a correctness diagnostic,
not a performance comparison. The candidate build and model were unchanged;
the opt-in setting was the only intervention.

## Result

The cache-3,000 two-live target-only reproducer has a prompt-specific mismatch
at generated token 60 with the default GR-V3 path. Its committed GDN state first
changes at model position 105, layer 24. At that position the selected token is
7620; recurrent state differs in 786,163/786,432 values (relative L2
0.0004944), and convolution state differs in 10,240/30,720 values (relative
L2 0.0014361).

Disabling the batched decoder with `STRATA_DEC_BATCH=0` did not remove this
position-105 layer-24 state difference. The state remained bit-exact through
layer 23. Minimum physical availability was 14.0 GiB.

With `STRATA_GR_V3=1`, the same target prompt's committed GDN state was
bit-identical to its serial control across all 36 layers at position 105. Its
generated token sequence matched serial for 72/72 tokens, including past the
default path's token-60 mismatch. Minimum physical availability was 14.0 GiB,
with no sampled cgroup memory events. The other concurrent prompt had no serial
control in this capture and is excluded from the parity claim.

A same-profile capture at positions 105 and 138 also matched all 72 target
tokens. State was exact at position 105, then first changed at position 138,
layer 2: recurrent state differed in 782,209/786,432 values (relative L2
`4.5873e-5`) while that layer's convolution state remained exact. Thus the
opt-in path delays this observed state onset past the default path's p105
boundary but does not keep persistent state bit-identical through the tested
output range. At position 138, layer 24 recurrent and convolution state differed
in 786,431/786,432 and 30,720/30,720 values respectively.

Follow-up state samples place the first changed layer-2 committed state at
position 134: position 133 was exact, while recurrent state at 134 differed in
782,604/786,432 values (relative L2 `7.35996e-5`) and convolution state in
10,235/30,720 values (relative L2 `2.12249e-4`). Layer 0 and 1 remained exact.
At that same position, layer-1 expert 75 had identical input activation, route
IDs, and route weights, but its owner changed from GPU in serial to CPU in the
batch row. It was the only changed expert part: 1,544/2,560 values differed
(maximum absolute delta `2.7269e-5`, relative L2 `6.0830e-4`). The combined MoE
output changed in 1,544/2,560 values (maximum `2.7511e-6`, relative L2
`7.6955e-5`), and layer-2 input `x` then differed in 2,554/2,560 values. The
independent native oracle matched the serial service part to its GPU output and
the batch service part to its CPU output bit-for-bit. This confirms an
owner-specific contribution at this sampled boundary; it does not show that it
is the only source of long-chain state drift.

At position 138, layer-2 `x`, `qkv`, `h`, `gate`, `beta`, and `z` were exact,
with `y` the first changed stage field (6,072/6,144 values; relative L2
`1.9768e-5`). The earlier position-134 state delta means this later stage
comparison does not isolate a new arithmetic cause.

A temporary profile moving layer-1 expert 75 from rank 5,362 to rank 0 was not
a usable repair: the target batch output first differed from serial at token
30, before the position-134 comparison could be paired. The opt-in exp2f SiLU
CPU selector also produced the same expert output as the default CPU oracle for
the captured activation. Neither candidate is promoted.

This is a reproducible local correction for one prompt pair and one position
range. It does not establish long-chain state parity, held-out quality, or a
performance benefit. Earlier 128-token GR-V3 evidence found accepted-prefix
hash changes later in the chain; Phase 5 remains open and the opt-in setting is
not promoted.

## Reproduction

The capture harness and raw `.stgcmt`, request JSON and supervisor logs remain
local in the following directories and are intentionally not committed:

- `2026-10-24-phase5-coder-slot1-first-divergence-p105-input/`
- `2026-10-24-phase5-coder-slot1-first-divergence-dec-batch-off/`
- `2026-10-24-phase5-coder-slot1-first-divergence-gr-v3/`
- `2026-10-24-phase5-coder-slot1-first-divergence-gr-v3-72/`
- `2026-10-24-phase5-coder-slot1-grv3-state105-138/`
- `2026-10-24-phase5-coder-slot1-grv3-state138-boundary/`
- `2026-10-24-phase5-coder-slot1-grv3-layer2-onset-sweep/`
- `2026-10-24-phase5-coder-slot1-grv3-layer2-onset-133-135/`
- `2026-10-24-phase5-coder-slot1-grv3-first-state-change-p134/`
- `2026-10-24-phase5-coder-slot1-grv3-expert75-rank0/` (rejected profile)

Common settings were target-only decode, two live rows, context 1,024,
3,000 expert-cache slots, 64-token prefill chunks, eight pool workers, MTP
disabled, `STRATA_NATIVE_CPU_Q8_1_DOT=all`, and `STRATA_IQ_MT_MIN=1`. State
comparisons used `tools/integration/compare_gdn_commit_state.py`. Physical
batch slots were mapped independently in each run by matching the captured
token stream to the serial prompt; the mapping reversed between runs. Do not
join captures by slot number alone.
