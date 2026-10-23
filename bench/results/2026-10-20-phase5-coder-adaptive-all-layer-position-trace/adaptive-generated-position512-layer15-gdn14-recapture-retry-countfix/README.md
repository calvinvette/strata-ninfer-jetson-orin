# Generated position 512 verifier and GDN state recapture — Orin — 2026-10-20

This randomized same-service `short-short-short` pair rechecked generated
position 512 after a previous trace appeared to show a host activation change
at layer 13. It used the pinned Coder IQ1_M GGUF (revision
`5348543e0147355ac9cbcb031184a3546350988e`) and PLE pack, current candidate
binary SHA256 `081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`,
seed 20261126, zero prompt cache, and four same-prompt requests per arm. Each
request generated 12 tokens. Delayed adaptation (`adapt_every=100000`) ran
before cap-8 adaptive migration (`adapt_every=4`, `adapt_swaps=8`).

Both supervised arms passed. Minimum host/admission availability was 14.12
GiB for delayed control and 14.25 GiB for adaptive; sampled cgroup memory event
counters remained zero. All generated token IDs matched across the four
requests in each arm.

The CUDA-side verifier capture found all 48 layer inputs at position 512
bit-identical across all four requests in both arms (192 layer-input records
per arm). Raw layer-14 GDN pre/post state was also
bit-identical across all request transitions, and each raw state hash matched
the service's layer-14 fingerprint. In the adaptive arm, accepted-prefix state
and GDN hashes first differed at zero-based indexes 10 and 11 between the
initial and intermediate requests; the intermediate-to-recovery transition
matched. Delayed-control accepted state remained exact.

The all-layer CPU-dispatch trace contains ownership changes but has unavailable
host activations for dispatches whose experts were all GPU-owned. Those rows
are explicitly marked invalid and were excluded from activation comparisons.
No valid selected host activation difference was observed at position 512, so
this capture does not locate the later accepted-state change. It shows only
that the sampled position-512 verifier inputs and layer-14 GDN state were
exact in this seed/history. The follow-up captures positions 521 and 522, where
the accepted-prefix state hashes diverged.

This is correctness localization, not a migration fix or performance result.
Raw service logs, traces, supervisor data and machine-readable comparisons are
retained here. The run harness initially failed to account for the optional
fourth continuation in one record-count check; the corrected retry is the
evidence reported above.
