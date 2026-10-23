# Layer-7 GDN hook selections — unsupported cell — Orin — 2026-10-20

This retained randomized-pair attempt used the pinned Coder IQ1_M model and
the combined layer-1/3/4/6 Q8_1 mirror selector while requesting layer-7
intermediate, verifier, raw-state, and committed-state captures. The delayed
control service exited during initialization, before any request ran. The
engine log states that GDN state capture needs a valid GDN layer, path, and
token positions. Source validation rejects raw GDN state capture on QSA layers;
layer 7 is a QSA layer in this model, so there is no GDN recurrent state to
capture.

A second attempt removed state capture but still requested layer-7 GDN
intermediates. The delayed-control request sequence ran, then the runner failed
because the requested verifier GDN capture was not emitted. No adaptive arm
ran. Both attempts are failed/unsupported instrumentation cells, not model or
adaptive-migration evidence.

The supported follow-up removes both raw GDN state and GDN intermediate hooks,
while retaining layer-7 MoE verifier and dispatch captures. It is recorded in
the adjacent `adaptive-layer1-3-4-6-combined-mirror-layer7-prompt-tail505-511-moe-only-pair`
directory. Do not infer that a missing state or GDN file means equal state or
intermediates.
