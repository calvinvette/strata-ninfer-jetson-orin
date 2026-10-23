# Current-source layer-16 expert to layer-17 GDN boundary — Orin — 2026-10-20

This randomized, supervised short/long/recovery pair used the pinned Coder
IQ1_M GGUF at revision `5348543e0147355ac9cbcb031184a3546350988e` and current
candidate binary SHA256
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. Both
arms generated eight tokens per request with `STRATA_NATIVE_CPU_Q8_1_DOT=all`.
At accepted position 515, it captured the layer-16 verifier input, expert
routes/parts/combined output, layer-17 GDN intermediates and raw pre/post state.
Both 28-GiB supervisors passed with zero cgroup events; minimum
host/admission availability was 14.26 GiB (adaptive) and 14.32 GiB (delayed).

For adaptive initial versus recovery, the token ID, layer-16 verifier input
bytes, expert IDs and router weights match. The input SHA256 is
`3586bf67c17963bfa134911d410a149d8cd782800c81bcb4c7b025f66300a4a2`. The
shared-expert output and nine routed expert rows are bit-identical. Only rank 7,
expert 118, differs (all 2,560 values; relative L2 `1.35199e-4`). The combined
layer-16 MoE output differs in 2,557/2,560 values (relative L2 `2.50977e-5`).
The same-binary position-515 dispatch trace separately records expert 118
changing CPU-to-VRAM ownership; an independent same-input oracle matched the
service CPU row and showed the corresponding CPU/GPU output delta. Expert 39
also changed owner in that trace, but its CPU/GPU oracle outputs were exact.

At layer 17, `x` is the first differing captured GDN field: 2,555/2,560 values
differ (relative L2 `7.73436e-6`). The raw pre-state is bit-identical. After
the update, 785,280/786,432 recurrent values differ (relative L2
`2.11060e-4`) and 10,232/30,720 convolution-history values differ. Delayed
control has exact layer-16 input, routes, expert rows, MoE output, all captured
layer-17 GDN fields and raw state across the same transition.

This joins an owner-dependent layer-16 expert-118 output change to the next
layer's first changed GDN input and state update on the current binary. It
strongly identifies expert 118 arithmetic as the immediate contributor in this
sample. The capture did not intervene on that row or isolate the full
residual/hyper-connection update, so it does not prove a complete causal fix or
bound drift for other tokens and profiles. This is correctness localization,
not a performance comparison; Phase 5 remains open.

Raw binary captures, route and request records, analyzers, service logs and
supervisor telemetry are retained in the two arm directories. The related
[64-token state repeat](../adaptive-current-081212f0-layer17-common-prefix-samples/README.md)
confirms divergence before generated tokens split; the prior
[layer-17 intermediate report](../adaptive-current-081212f0-layer17-position515/README.md)
contains the detailed field-by-field GDN comparison.
