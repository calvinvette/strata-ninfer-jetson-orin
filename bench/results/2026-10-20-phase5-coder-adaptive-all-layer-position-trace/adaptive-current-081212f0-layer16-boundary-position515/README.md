# Current-source layer-16 residual boundary — Orin — 2026-10-20

This randomized, supervised short/long/recovery pair used the pinned Coder
IQ1_M model at revision `5348543e0147355ac9cbcb031184a3546350988e` and
candidate binary SHA256
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. It
captured layer-16 MoE rows, residual/hyper-connection fields around layer 16,
layer-17 GDN intermediates and raw state at accepted position 515. Both arms
used `STRATA_NATIVE_CPU_Q8_1_DOT=all` and generated eight tokens per request.
Both supervisors passed with zero cgroup events and at least 14.16 GiB
host/admission availability.

In the adaptive initial/recovery comparison, the layer-16 residual field `R`,
injection field `inj2`, and `before_next_read_R` are bit-identical. The
post-layer `bo` field differs in 2,557/2,560 values (relative L2
`2.50977e-5`), matching the changed combined layer-16 MoE output. After the
next read, 9,092/10,240 values in `R` and 8,898/10,240 values in `xn` differ;
the `xn` relative L2 is `6.09090e-6`. This directly records the layer-16 MoE
delta entering the following layer's residual/GDN input path. Delayed control
is bit-identical in every captured field.

Joined with the [layer-16 expert and layer-17 GDN capture](../adaptive-current-081212f0-layer16-to17-position515/README.md),
the evidence path is: unchanged layer-16 input and routing; expert 118's output
row changes; the combined layer-16 output and `bo` change; the subsequent
residual/read `xn` changes; then layer-17 GDN `x` and recurrent state change.
A same-binary dispatch trace and same-input oracle identify the CPU-to-VRAM
owner change and arithmetic delta for expert 118. This is strong localization
for the sampled transition, not a controlled intervention proving a general
correction or an error bound. Phase 5 remains open.

The original analyzer assumed three records and failed on this two-request
capture. `compare_residual_boundary.py` now compares every adjacent pair for
any accepted record count of at least two; the retained analysis JSONs were
generated from both actual pair captures. Raw boundary dumps, service logs,
campaign metadata and supervisor telemetry remain in the arm directories.
