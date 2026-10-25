# NInfer E5 bounded closeout

Date: 2026-10-25. E5 is complete for the tested single-live, static-residency
Q2_0/Q2_0 CUDA profile only. This records functional integration evidence; it
does not make a performance claim or generalize to mixed codecs, adaptive
residency, concurrent requests or other hardware.

## Qualified test boundary

The tested model is the ISTA-DASLab Coder Q2_0 artifact, 48 layers, Q2_0
gate/up/down experts and 2560/640 geometry. Services used strict NInfer,
3,000 static expert slots, 8K configured context, FP16 KV, prefill 128 and eight
workers on Orin AGX / CUDA 12.6 / SM87. The supported MTP settings are off, 2
and 4 for the documented cells:

- MTP-2 and MTP-4 cancellation followed by same-process recovery matched exact
  fresh reference states at tested accepted lengths.
- MTP-off versus MTP-2 and MTP-4 matched token IDs and persistent state at all
  shared accepted prefixes on the 512-token task.
- A three-request MTP-off/MTP-4 sequence matched tokens and nine state fields
  across initial generation, continuation and recovery, including after
  rejected drafts.
- The exact retrieval-plus-arithmetic answer passed at 512 and 4,096 prompt
  tokens. MTP-off and MTP-4 NInfer arms had identical token IDs and final state
  for each task.
- Verifier and MTP graph-instantiation events were observed in supervised
  sessions; cancellation, subsequent continuation and recovery completed.

Reports: [MTP-2 cancellation](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp2-cancel-state/README.md),
[MTP-4 cancellation](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp4-cancel-state/README.md),
[MTP-2 accepted prefixes](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp2-prefix-parity/README.md),
[MTP-4 accepted prefixes](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp4-prefix-parity/README.md),
[continuation/recovery](../../bench/results/2026-10-25-phase-e5-q2-ninfer-mtp4-continuation/README.md),
[512-token retrieval](../../bench/results/2026-10-25-phase-e5-q2-ninfer-retrieval-check/README.md),
[4K retrieval](../../bench/results/2026-10-25-phase-e5-q2-ninfer-long-retrieval/README.md).

## Deliberate exclusions and numerical boundary

Strict NInfer supports only Q2_0/Q2_0 at the stated geometry. Coder IQ1_M and
ISTA-DASLab IQ3_S remain unsupported. Adaptive CPU/GPU migration and multi-live
service execution are not qualified. A process must keep one expert backend
for its session; there is no Strata-to-NInfer live-state migration contract.

Fresh Strata-default and strict-NInfer services produced the same exact
retrieval answers at 512 and 4K, but their persistent-state fingerprints
differed. Direct GDN comparison at 512 measured relative L2 `0.0902` after the
first committed token and `0.0337` after the full answer. Captures found
bit-exact layer 0; at layer 1, expert-part relative L2 was `2.94e-8`; at layer
2, input relative L2 was `7.25e-4` and combined MoE output relative L2 was
`5.78e-3`. A separate natural-generation sample first differed at token 9 and
returned coherent, nonidentical prose. These cross-backend deltas are recorded,
not treated as state parity or a quality failure by themselves. Their quality
effect outside the tested tasks is unknown.

The numerical contract is therefore scoped: accepted-prefix parity is required
and passed within one static NInfer service across MTP policies; exact state
equivalence to Strata is not claimed. Future comparisons must use task-scoring
checks in addition to token text and must not switch backend within a live
session.

The bounded E5 matrix is complete. Broader task quality, codecs, adaptation,
multi-live traffic, CPU/HIP/SYCL runtime and performance remain outside this
closeout and stay open in later stages.
