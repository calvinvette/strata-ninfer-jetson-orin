# Layer-7 GDN-state hook selection — unsupported cell — Orin — 2026-10-20

This retained randomized-pair attempt used the pinned Coder IQ1_M model and
the combined layer-1/3/4/6 Q8_1 mirror selector while requesting layer-7
intermediate, verifier, raw-state, and committed-state captures. The delayed
control service exited during initialization, before any request ran. The
engine log states that GDN state capture needs a valid GDN layer, path, and
token positions. Source validation rejects raw GDN state capture on QSA layers;
layer 7 is a QSA layer in this model, so there is no GDN recurrent state to
capture there. The pair is marked failed/unsupported instrumentation, not model
or adaptive-migration evidence.

The first follow-up removed the raw state hooks but still requested a layer-7
GDN intermediate file. The pair ran its delayed-control requests, then the
runner failed because the requested verifier GDN capture was not emitted for
this QSA layer. That second selection is also retained as an unsupported
instrumentation cell in the adjacent
`adaptive-layer1-3-4-6-combined-mirror-layer7-prompt-tail505-511-no-state-pair`
directory. The valid follow-up removes both GDN state and GDN intermediate
hooks while keeping the layer-7 MoE verifier and dispatch captures. Do not
infer that a missing state or GDN file means equal state or intermediates.
