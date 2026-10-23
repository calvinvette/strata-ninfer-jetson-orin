# Layer-27 Q8_1 owner mirror — Orin — 2026-10-20

This short-only pair added the layer-27 IQ3_S/IQ4_NL Q8_1 mirror to the
existing layer 1/3/4/6/8/9/10/11/12/13/15/16/19/24 selector set. It used seed
20261080, three repeated 512-token requests, a 12-token generation limit and
no prompt cache on the pinned Coder IQ1_M artifact. Candidate binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. Both
supervised arms passed with at least 14.12 GiB host/admission availability and
zero cgroup events.

The same-input native oracle makes expert 175's CPU/CUDA output bit-identical.
All three verifier expert rows and combined layer-27 MoE outputs match both
oracle paths. The next layer's verifier `ffn_y` still differs, while layer-28
input and raw committed GDN state remain exact. The first changed recorded
dispatch input moves to layer 29. Adaptive accepted-state hashes still differ
at all 12 prefixes; delayed control remains exact.

The opt-in mirror closes this selected operator difference only. It does not
restore the full adaptive state chain or establish a drift bound; Phase 5
remains open. Raw service captures, oracle, analyses and launch telemetry are
retained in this directory.
