# IQ4_NL down-projection reduction match

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a targeted E5
numerical correction and repeatability check for Coder IQ1_M, not an E5-wide
quality result or a performance qualification.

## Change and operator oracle

The NInfer IQ4_NL down kernel now follows Strata's native CUDA arithmetic for
the 640-wide intermediate: 16-value fragments, the same fragment scaling and
eight-lane reduction order. The CUDA targets `strata` and
`ninfer_iq_expert_parity` rebuilt successfully. On the captured layer-0
position-41 activation, one routed expert from each of the 48 Coder layers was
replayed. All 48 outputs matched the native CUDA oracle bit-for-bit across
seven observed codec tuples. Gate/up outputs and all hidden Q8_1 bytes also
matched for every row. This includes 39 IQ4_NL-down rows across IQ2_S,
IQ3_XXS, IQ3_S and IQ4_XS gate/up formats, plus nine Q2_0-down rows as a
regression screen. Before the change, the five GPU-owned layer-0 rows differed
by relative L2 `8.39e-8`–`8.54e-8`; the five CPU-owned service rows were already
exact.

The paired service capture at position 41 also compared all MoE bundle fields
for every layer: route IDs and weights, MoE inputs, expert parts, shared output
and combined output were exact across all 48 layers.

## Service accepted-prefix checks

Two supervised Strata/strict-NInfer service pairs used the same Coder IQ1_M
two-shard model, static profile, prompt IDs `[1,2,3]`, eight-token greedy
generation, MTP-2, a 1 GiB pinned complement, PCIe share 1.0, six-GiB host
headroom and adaptation disabled. Each pair emitted
`[4,5,6,24218,10,4838,1665,15]`. The layer-0 owner capture selected identical
routes in each pair: four primary-GPU and six PCIe rows, with no CPU output
rows. All eight accepted-prefix boundaries had exact equality across GDN,
PLE, tail, pooled, pooled-full, KV, MTP, stale, dead and PLE previous-token
hashes in both runs.

The same setup with the prior reduction order had the same token sequence but
diverged in persistent state at all eight boundaries, starting with the first
token. This makes the reduction-order correction the controlled source change
associated with restored state parity in these two repeats. It does not prove
parity for other prompts, contexts, adaptive residency or MTP draft
acceptance. A separate one-token `is_even(n)` service pair also returned token
`71093`, matched every recorded final persistent-state hash and produced
identical GDN dumps (SHA-256
`6bd92b0e4f9da1d81a5377e1d4321bfdd5fd2069a8abf56eecfb8213bcbb8b63`).

Both supervised pairs passed the physical-memory guard with minimum available
RAM of 19.89 and 19.64 GiB. The pre-existing cgroup OOM-kill count stayed at
one. Clocks were observed and dynamic; EMC readback was denied; energy was not
measured. Trace/hash instrumentation was enabled and requests ran sequentially,
so service timing values are excluded from performance claims. See
[`comparison.json`](comparison.json) and the [48-layer
matrix](all-layer-matrix.json) for machine-readable state, codec and telemetry
audits. Raw logs, owner activation arrays and other captures remain in `/tmp`.

## Remaining work

Repeat numerical checks across varied natural tasks and longer accepted-prefix
runs. Measure this change with randomized paired kernel and service timing
before making a throughput claim.
E5 broad state/quality coverage, E6 performance qualification and E7 release
assessment remain open.
