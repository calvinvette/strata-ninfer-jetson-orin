# Current-source layer-17 raw GDN capture — Orin — 2026-10-20

This randomized short/long/short pair used binary
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d` and the
pinned Coder IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e`. It captured layer-17 verifier
intermediates and raw pre/post GDN state at accepted position 515, with eight
generated tokens per request, `STRATA_NATIVE_CPU_Q8_1_DOT=all`, and
`MemoryMax=28G`.

For adaptive initial-short versus recovery-short, the raw layer-17 pre-state
was bit-identical. The layer-17 `x` field already differed in 2,555/2,560
values, with relative L2 `7.7344e-6` and maximum absolute difference
`1.7226e-5`. This is the first differing captured GDN field. After the token,
785,280/786,432 recurrent values and 10,232/30,720 convolution values differed.
The post-state bytes match service GDN hash ordinal 13 in both requests. Thus
the recurrent update did not start from a changed raw state; its captured input
`x` was already different. The subsequent GDN and FFN fields show larger
downstream deltas. This does not identify which earlier operation first
changed `x`.

Delayed control matched the raw pre/post state and all ten captured GDN
intermediate fields bit-for-bit across the same initial/recovery transition.
At layer 16 the all-layer trace found identical dispatch activations and expert
IDs but CPU/GPU owner changes for experts 118 and 39. That is a plausible
upstream path to inspect, not proof that either expert caused the `x` delta;
this layer-17 capture did not include layer-16 expert outputs. Both
supervisors passed with zero cgroup events. This is one correctness pair, not
a quality or performance result.

A separate [layer-16 service-row capture](../adaptive-current-081212f0-layer16-service-cpu-output/README.md)
verified both CPU rows against same-input oracles. A [temporary direct-division
SwiGLU trial](division-formula-trial/README.md) did not change expert 118's CPU
output or its CPU/CUDA delta. Stage checks found exact Q8_1 inputs and gate/up
dots, three hidden-block scale-byte differences, and an exact CPU down
projection on CUDA hidden blocks. The candidate was rejected; the source and
parity target were restored to the reciprocal form.

`state-prefix-analysis.json` verifies raw post-state against the accepted
service hashes. `adaptive-gdn-intermediate-analysis.json` and
`delayed-gdn-intermediate-analysis.json` compare all captured fields. Raw
intermediate/state files and supervisor logs remain in their arm directories.
The [position-515 dispatch report](../adaptive-current-081212f0-position515/README.md)
records the preceding all-layer capture. Phase 5 remains open.
