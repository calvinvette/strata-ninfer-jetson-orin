# Layer-27/29 Q8_1 owner mirrors — Orin — 2026-10-20

This is a short-only same-service pair with the existing layer 1/3/4/6/8/9/
10/11/12/13/15/16/19/24 selectors plus Q8_1 mirrors at layers 27, 28 and 29.
It used seed 20261082, three repeated 512-token requests, a 12-token
generation limit and no prompt cache on the pinned Coder IQ1_M artifact.
Candidate binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. Both
supervised arms passed with at least 14.15 GiB host/admission availability and
zero cgroup memory events.

At layer 29, expert 143 changes CPU-to-CUDA with identical input, expert IDs
and router weights. The native Q8_1 oracle and all three service rows match
bit-for-bit; the combined layer-29 output remains exact. Layer-28 GDN
intermediates and raw committed state remain exact and cross-check to service
hashes. The first changed recorded dispatch input moves to layer 31.

Adaptive accepted-state fingerprints still differ at all 12 compared
prefixes, despite matching adaptive initial/recovery token IDs in this run.
Delayed control remains exact. This opt-in mirror does not establish a general
drift bound or repair adaptive migration; Phase 5 remains open.
