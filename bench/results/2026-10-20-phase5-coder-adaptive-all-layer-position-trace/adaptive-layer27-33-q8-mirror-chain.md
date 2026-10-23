# Adaptive owner-mirror chain — Orin — 2026-10-20

This diagnostic chain follows same-prompt, three-request adaptive migration
captures on the pinned Coder IQ1_M artifact, revision
`5348543e0147355ac9cbcb031184a3546350988e`, using service binary SHA256
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. The
selector is opt-in. The requests used a 512-token prompt, 12 generated tokens,
no prompt cache and a 28-GiB supervisor. These are correctness interventions,
not independent performance replications. All listed campaigns passed
supervision, retained at least 14.10 GiB host/admission availability and had
zero cgroup memory events.

The earlier [layer-27/28 default-arithmetic capture](adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/README.md)
showed expert 175 moving CPU-to-CUDA on the same activation, route IDs and
router weights. The service rows matched owner-specific native oracles, while
the combined MoE output changed. Layer-28 `x` and committed state then changed.
Adding the Q8_1 mirror for layer 27 made that expert row bit-identical across
owners and kept layer-28 raw state exact, but accepted-prefix hashes still
differed. The first captured dispatch-input difference moved to layer 29.

The follow-up pairs added one target at a time to the same selector set:

| Added Q8_1 mirror | Service-level oracle result | First captured boundary / result |
| --- | --- | --- |
| Layer 28, expert 36 | CPU and CUDA oracle rows match; layer-28 `ffn_y` is exact | First changed dispatch input moved to layer 30; layer-28 raw state exact; adaptive recovery differed by 9/12 token IDs in this run. [Capture](adaptive-layer27-28-q8-mirror-state28-pair/) |
| Layer 29, expert 143 | CPU and CUDA oracle rows match on the captured input | First changed dispatch input moved to layer 31; layer-28 raw state exact; token IDs matched in this run. [Capture](adaptive-layer27-29-q8-mirror-state28-pair/) |
| Layer 30, experts 121 and 212 | Both service expert rows match CPU and CUDA Q8_1 oracles; combined MoE output is exact across three requests | First changed dispatch input moved to layer 34; layer-28 raw state exact; token IDs matched in this run. [Capture](adaptive-layer27-30-q8-mirror-state28-pair/) |
| Layer 33, expert 57 | The first two verifier rows match the same-input CPU/CUDA oracle; the third request's layer-33 verifier input already differs | Global accepted-state hashes still differ at all 12 prefixes and recovery differs by 9/12 token IDs. [Capture](adaptive-layer27-33-q8-mirror-state28-pair/) |

The [layer-27-only mirror pair](adaptive-layer27-q8-mirror-short-short-short-state28-pair/)
also made expert 175's service rows match both Q8_1 oracle paths and moved the
first captured input difference to layer 29, while accepted-state hashes still
differed. The standalone layer-33 parity run reports exact CPU/CUDA selected
outputs for expert 57; a separate standalone down-projection schedule
diagnostic differs from the grouped service schedule and is not used as a
service-output claim.

The selected-position dispatch file records two endpoint request traces in
these campaigns, while verifier captures record three requests. Do not read a
two-row all-layer comparison as covering the omitted request: in the layer-33
pair, the third verifier input differs from the same-input oracle activation.
The exact committed GDN layer-28 dump was cross-checked against service hashes;
it is only one layer's state, not total model-state parity.

The 96-row layer-33 trace above was followed by a [144-row recapture](adaptive-layer27-33-q8-mirror-all-three-dispatch-state28-pair/README.md)
with three complete dispatch blocks and all three layer-33 verifier records.
It confirms that initial-to-intermediate activations and expert IDs match,
while adaptive owners change at ten layers. Intermediate-to-recovery first
changes the dispatch activation at layer 32; IDs change at layers 32, 34, 39,
43 and 47. The third adaptive layer-33 verifier input does not match the oracle
activation, while the earlier two do. Adaptive accepted-state hashes still
differ at all 12 prefixes and recovery differs at 9/12 token IDs. The earlier
two-row coverage limitation is corrected by this follow-up, but the measured
state divergence remains.

The evidence supports targeted CPU/CUDA operator equivalence for the listed
captured rows. It does not establish general adaptive-migration parity, an
accepted-state drift bound, answer-quality preservation across these selector
chains, or a performance improvement. No default changed; Phase 5 remains
open. Full commands, raw captures, oracle outputs, comparison JSON and
supervisor telemetry remain in each linked result directory.
