# Layer-27/30 Q8_1 owner mirrors — Orin — 2026-10-20

This short-only pair added Q8_1 mirrors at layers 27, 28, 29 and 30 to the
existing layer 1/3/4/6/8/9/10/11/12/13/15/16/19/24 selectors. It used seed
20261083, three repeated 512-token requests, 12 generated tokens, no prompt
cache and the pinned Coder IQ1_M model. Candidate binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. Both
28-GiB supervised arms passed with at least 14.16 GiB host/admission
availability and zero cgroup memory events.

At layer 30, the dispatch input and routed IDs match between the two captured
endpoints. Experts 121 and 212 match their same-input CPU and CUDA Q8_1 oracles
bit-for-bit in all three verifier rows. The combined MoE output also remains
bit-identical across those rows. Layer-28 raw committed state is exact and
cross-checked to service telemetry. The first changed recorded dispatch input
moves to layer 34.

Adaptive accepted-state fingerprints still differ at all 12 compared
prefixes, although adaptive initial/recovery token IDs match in this run.
Delayed control remains exact. This is a targeted correctness intervention,
not a general migration fix or performance result; Phase 5 remains open.

Raw captures, both operator oracles, analysis JSON, launch records and
supervisor telemetry are retained in this directory.
