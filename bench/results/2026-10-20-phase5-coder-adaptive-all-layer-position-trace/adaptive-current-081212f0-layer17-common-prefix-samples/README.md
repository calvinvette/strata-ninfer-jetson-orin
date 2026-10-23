# Current-source 64-token layer-17 raw-state samples — Orin — 2026-10-20

This same-service short/long/recovery pair used the pinned Coder IQ1_M model
(Hugging Face revision `5348543e0147355ac9cbcb031184a3546350988e`) and current
candidate binary SHA256
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. Both
arms generated 64 tokens per request, used
`STRATA_NATIVE_CPU_Q8_1_DOT=all`, captured layer-17 verifier raw state at
positions 515, 519, 522 and 527, and ran under separate `MemoryMax=28G`
supervisors. The randomized order was adaptive cap-8, then delayed control.

Both supervisors passed with zero cgroup memory events. Minimum host/admission
availability was 14.09 GiB for adaptive and 14.31 GiB for delayed control.
Delayed control returned identical initial/recovery token IDs and persistent
state fingerprints. Its sampled layer-17 pre/post raw states were bit-identical
at all four positions.

Adaptive initial and recovery tokens match through accepted position 533 and
first differ at position 534; 40 of 64 token IDs differ overall, and terminal
persistent-state fingerprints differ. The service's per-GDN hashes first
differ at accepted position 515, ordinal 13 (model layer 17). At that position,
the layer-17 recurrent and convolution pre-state is bit-identical, but the
captured post-state differs in 785,280/786,432 recurrent values (relative L2
`2.1106e-4`) and 10,232/30,720 convolution values. At positions 519, 522 and
527, recurrent pre/post state also differs while convolution history remains
exact. Captured tokens match at all four positions. The earlier
[eight-token layer-17 intermediate capture](../adaptive-current-081212f0-layer17-position515/README.md)
found the first changed captured field was `x` before the recurrent update.
Together these results confirm the boundary over the longer continuation but
do not identify the upstream operation that first changes the layer-17 input.

The original attempt also requested position 575. The runner correctly marked
that cell failed because the verifier emitted no records at 575; the complete
failed arm and telemetry remain under
`adaptive-current-081212f0-layer17-state-samples/`. No memory guard failed.
The successful rerun used only positions observed in both short requests.

Raw state dumps, service logs, request outputs, per-GDN comparisons, campaign
metadata and supervisor telemetry are retained in the arm directories. This is
sampled correctness localization for one model, binary and prompt sequence; it
does not bound unobserved positions or generalize to other profiles. Phase 5
remains open.
