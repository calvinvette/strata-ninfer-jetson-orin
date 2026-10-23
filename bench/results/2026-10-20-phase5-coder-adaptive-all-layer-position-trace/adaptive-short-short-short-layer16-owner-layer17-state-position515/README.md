# Layer-16 dispatch and layer-17 state capture — Orin — 2026-10-20

This randomized short/short/short adaptive pair captures the layer-16 dispatch
and layer-17 GDN intermediate/raw state at position 515. Both arms used the
pinned ISTA-DASLab Coder IQ1_M shards (revision
`5348543e0147355ac9cbcb031184a3546350988e`) and the same candidate binary.
The delayed control remained exact across the three requests. Adaptive token
IDs also matched, but accepted state first differed between the first and
second requests and then repeated exactly between the second and third.

At layer 16, position 515, activation, expert IDs and router weights matched
across requests. Experts 118 and 39 changed from CPU to VRAM ownership between
the initial and recovery routes. Expert 118's route and input are retained
beside its same-input native CPU/GPU oracle in `expert118-oracle/`.

The direct CPU owner capture is in the linked
[validated follow-up](../adaptive-short-short-short-layer16-cpu-owner-output-position515-validated/README.md).
The initial CPU oracle used its default arithmetic mode and was not comparable
to the service configuration. Repeating it with the service
`STRATA_NATIVE_CPU_Q8_1_DOT=all` selector matched the captured CPU-pool row to
relative L2 9.51e-10. The same-input CPU/GPU outputs differed by 0.01352%
relative L2. Expert 39, the other migrating expert, has bit-identical CPU and
CUDA oracle output and contributes no measured owner-path delta. The weighted
owner-transition estimate is therefore carried by expert 118 (L2 norm
1.36e-5), under the unchanged-input/route assumptions recorded in
`owner-transition-contribution-analysis.json`. The verifier-parts capture is
the verifier's assembled per-expert buffer after CPU rows are copied and GPU
hit rows are added; it is the mixed-owner data consumed by weighted combine,
not an independent CUDA-only tensor. A later same-service
[cross-check](../adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md#verifier-parts-capture-semantics-cross-check)
matched direct CPU rows to this buffer within JSON serialization precision.
This validates these selected operator rows but does not isolate the
downstream state divergence or establish a performance result.

At layer 17, position 515, the first differing captured GDN field is `x`. The
raw layer-17 pre-state matches across the initial/intermediate request; after
the position, 785,280/786,432 recurrent values and 10,232/30,720 convolution
values differ. The intermediate/recovery transition is exact. Raw post-state
hashes cross-check against service GDN ordinal 13. The layer-17 MoE input and
router weights already differ, so the current evidence does not isolate the
layer-16 transition as the cause.

Both supervised paired runs passed with at least 14.14 GiB minimum host and
admission availability, no change to system clocks/services, and no sampled
cgroup pressure events. This is correctness diagnostics, not a performance
comparison or completion of Phase 5.
