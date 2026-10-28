# Layer-3 upstream trace and layer-4 state check

Paired staged-backend diagnostic on the Orin AGX, using Q2_0, the 163,840-token
held-out retrieval prompt, and the same strict NInfer/Strata settings. Both arms
returned the exact expected answer and identical 47 token IDs and residency.
Final persistent `gdn`, `tail`, `pooled`, `pooled_full`, and `kv` fingerprints
differed. The request wrapper returned 1 for that state mismatch; this is not a
performance run.

## Observations

| Capture | Result |
| --- | --- |
| Boundary after model layer 2 | Runtime relative L2 `9.70e-5`; MoE row `3.86e-3`; next-layer `xn` `1.14e-3` |
| Boundary after model layer 3 | Runtime relative L2 `1.05e-3`; MoE row `1.41e-2`; next-layer `xn` `4.57e-3` |
| Layer-3 QSA at position 163885 | Selection equal; QSA input, query, index query, current K/V, attention, gated attention, projected output and MoE input differ |
| Layer-3 MoE at position 163885 | Route IDs equal; expert parts relative L2 `1.26e-2`; shared output `2.20e-2`; combined output `1.41e-2` |
| Layer-4 committed state, before token 23 | Relative L2 `4.48e-3` (state after token 21) |
| Layer-4 committed state, after token 23 | Relative L2 `4.41e-3` |
| Layer-4 raw GDN `o` / normalized `y` | Relative L2 `2.14e-3` / `5.84e-3` |
| Independent FP64 recurrence replay | Relative L2 `8.66e-8` Strata; `8.07e-8` NInfer |

The state was already different before the captured layer-4 step, while both
implementations independently replay the captured recurrence accurately. This
pair therefore does not implicate the layer-4 recurrence. At the selected
position, QSA selection metadata agrees, but numerical QSA inputs and outputs
do not; layer-2 boundary values already differ. The capture does not identify a
stable earliest cause: earlier long-context pairs have placed the first small
split at different layers, and instrumentation can change the observed
trajectory. These measurements characterize this capture only.

## Resource and artifacts

The supervised run took 3,233.9 seconds. Minimum available physical memory was
7,136,874,496 bytes (6.65 GiB); peak swap was 2,297,270,272 bytes (2.14 GiB),
with no sampled OOM events. Raw captures remain in `run/`; the supervisor record
is in `supervisor/`. The numerical summaries are the adjacent JSON files for
boundary, QSA, MoE, GDN commit, GDN output and the two independent recurrence
oracles. No source changes or model files are included in this evidence.
