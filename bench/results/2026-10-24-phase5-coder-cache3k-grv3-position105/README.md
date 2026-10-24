# Coder cache-3k GR-V3 state intervention

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

Common settings were target-only decode, two live rows, context 1,024,
3,000 expert-cache slots, 64-token prefill chunks, eight pool workers, MTP
disabled, `STRATA_NATIVE_CPU_Q8_1_DOT=all`, and `STRATA_IQ_MT_MIN=1`. State
comparisons used `tools/integration/compare_gdn_commit_state.py`. Physical
batch slots were mapped independently in each run by matching the captured
token stream to the serial prompt; the mapping reversed between runs. Do not
join captures by slot number alone.
