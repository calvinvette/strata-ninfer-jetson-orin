# Three-request layer-27–33 Q8_1 capture with full dispatch coverage — Orin — 2026-10-20

This is the full 144-row follow-up to the earlier 96-row layer-27–33 capture.
It used the pinned Coder IQ1_M artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, service binary SHA256
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`, and the
opt-in layer-specific Q8_1 selector through layer 33. Both arms ran the same
three 512-token prompts with 12 generated tokens, prompt cache disabled, and
`MemoryMax=28G`. The captures include three complete 48-layer dispatch blocks
per arm, all three layer-33 verifier inputs and expert parts, and layer-28 raw
committed GDN state. This is correctness localization, not a performance test.

The initial-to-intermediate adaptive transition had identical captured
activations and expert IDs through all layers. Owner assignments changed at
layers 8, 13, 16, 19, 24, 27, 28, 29, 30 and 33. On the intermediate-to-recovery
transition, the first changed dispatch activation was layer 32; expert IDs
changed at layers 32, 34, 39, 43 and 47, and owner assignments changed at
layers 31, 32, 34 and 43. The delayed control had identical activations, expert
IDs and owners across both transitions.

The adaptive recovery differed from the initial request at 9/12 token IDs and
all 12 accepted-prefix state hashes. Layer-28 raw committed state remained
exact across the captured requests and matched service hashes, so this one
layer does not explain total model-state divergence. For the layer-33 oracle,
all three delayed-control rows and the first two adaptive rows had verifier
inputs matching the independent activation and expert outputs matching both
CPU and CUDA oracles. The third adaptive verifier input differed from the
oracle activation and its combined output differed in all 2,560 values; the
full dispatch capture now exposes that third request rather than implying
coverage from the earlier two-row trace.

Both supervisors passed in 106.64 seconds (adaptive) and 105.59 seconds
(delayed), with minimum host/admission availability of 14.13/14.27 GiB. Their
102/101 memory samples recorded zero `high`, `max`, `oom`, and `oom_kill`
events. The reports `selected-position-analysis.json`, `layer33-analysis.json`,
and `state-prefix-analysis.json` retain the comparisons; raw captures and
telemetry are in each arm directory. Phase 5 remains open.
