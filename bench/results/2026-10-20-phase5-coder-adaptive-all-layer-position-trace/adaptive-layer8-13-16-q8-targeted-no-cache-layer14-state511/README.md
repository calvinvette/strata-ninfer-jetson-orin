# Layer-13 mirror with no prompt cache and layer-14 state capture

This randomized short/short/short pair used prompt-cache capacity 0 with the
layer-8, layer-13, and layer-16 selectors:
`iq2_s/q2_0@layer=8,iq2_s/q2_0@layer=13,iq3_xxs/iq4_nl@layer=16`. It captured
layer-14 prefill and verifier state, layer-13 verifier MoE output, and all-layer
dispatches at position 511. Both arms passed supervision; minimum host/admission
availability was 14.12 GiB for adaptive and 14.10 GiB for delayed control, with
zero cgroup pressure/OOM events.

Layer-14 prefill hashes and raw state matched at all chunk boundaries and
across all three prompts in both arms. Raw layer-14 verifier pre/post state at
position 511 matched for adaptive initial-to-intermediate; the
intermediate-to-recovery pre-state matched, but post-state differed in
786,309/786,432 recurrent and 10,240/30,720 convolution values. Delayed control
was exact. Thus layer-13 mirroring removes this sampled layer-14 state write on
the first adaptive transition, but not on the second.

The two adaptive transitions have different first per-layer GDN mismatches:
initial-to-intermediate starts at ordinal 19 (model layer 25), while
intermediate-to-recovery starts at ordinal 9 (model layer 12). Comparing the
initial and recovery all-layer dispatches, the first activation difference is
layer 25 (relative L2 0.00230; max absolute delta 0.00622). Layer 24's expert
173 changes CPU-to-GPU owner with matching IDs; layer 13's expert 147 also
changes owner, despite matching input activation on the initial/recovery
capture. Recovery token IDs match all 12 positions, while accepted-prefix
fingerprints differ at all 12. This history-dependent split means the layer-13
mirror has not established request-level state correctness.

The next capture adds the known layer-24 IQ2_S/IQ4_NL mirror and measures the
layer-25 state boundary. It will test whether the first initial-to-intermediate
GDN mismatch at ordinal 19 follows the expert-173 owner transition. Captures
and per-request analyses are retained alongside this report.
