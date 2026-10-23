# Layer-28 mirror follow-up with no prompt cache

This randomized short/short/short pair used prompt-cache capacity 0 and
selectors at layers 8, 13, 16, 24, and 28. It captured layer-29 prefill and raw
verifier state, layer-28 verifier MoE output, and all-layer dispatches at
position 511. Both arms passed supervision. Minimum host/admission availability
was 14.16 GiB for adaptive and 14.21 GiB for delayed control; cgroup
pressure/OOM counters were zero.

Layer-29 prefill hashes and raw state matched at every boundary and across all
three prompts. Raw layer-29 verifier state at position 511 matched for the
adaptive initial-to-intermediate transition. The intermediate-to-recovery
pre-state also matched, but post-state differed in 786,416/786,432 recurrent
and 10,240/30,720 convolution values; delayed control was exact. The accepted-
prefix per-GDN mismatch starts at ordinal 23 (model layer 30) for
initial-to-intermediate and ordinal 15 (model layer 20) for
intermediate-to-recovery. Comparing initial with recovery, the first selected
activation difference moved to layer 30 (relative L2 0.00337; max absolute
delta 0.00904).

The layer-28 mirror makes the captured layer-29 state exact on the first
adaptive transition. Layer 28 still records CPU-to-GPU owner changes for
experts 146 and 36, but its exact layer-28 selector is enabled. At layer 29,
expert 143 changes CPU-to-GPU while its IDs and input activation match; the
native layer profile identifies the layer's weights as IQ3_S/IQ4_NL. This
expert is the next mirror candidate. Adaptive recovery differs from initial by
6 of 12 tokens and accepted-prefix state differs at all 12 generated prefixes.
The differing first GDN ordinal across adjacent transitions shows that this
remains history-dependent; these local captures do not prove layer 29 is the
only cause.
