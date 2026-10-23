# Layer-27–33 Q8_1 owner mirrors — Orin — 2026-10-20

This short-only same-service pair extended the prior Q8_1 selectors to layers
27, 28, 29, 30 and 33. It used seed 20261084, three repeated 512-token
requests, a 12-token generation limit, no prompt cache and the pinned Coder
IQ1_M model. Candidate binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. Both
supervised arms passed with at least 14.14 GiB host/admission availability and
zero cgroup memory events.

The layer-33 same-input Q8_1 operator oracle makes expert 57's CPU/CUDA output
bit-identical. Its first two verifier rows use the oracle activation and both
service rows match the CPU and CUDA outputs exactly. The third request's
layer-33 verifier input differs from that activation; its expert row differs
from both oracle outputs, so this request is not an oracle parity result. The
two-row dispatch capture contains identical activations with CPU and CUDA
owner encodings; it does not cover all three verifier requests.

Adaptive accepted-state hashes differ at prefixes 1–11 on the first-to-second
request comparison and at all 12 prefixes on initial-to-recovery. Recovery
differs by 9/12 token IDs from the initial request; the intermediate and
recovery token IDs match each other. Layer-28 committed state remains exact in
this capture, but this does not imply total model-state parity. Delayed control
remains exact. The selected mirrors do not establish a general adaptive
migration correction or drift bound; Phase 5 remains open.

`layer33-analysis.json` records per-request verifier-input identity and
oracle-join coverage. The raw route, verifier, GDN, accepted-state and
supervisor artifacts remain in this directory.
