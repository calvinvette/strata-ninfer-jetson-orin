# Repeated accepted-prefix GDN commit comparison

This repeated the exact three-position all-layer GDN capture described in the
[first report](../gdn-commit-all-3pos/README.md), using the same 160K Q2_0
workload, model, context, and backend settings. Both arms again returned the
exact answer and same 47 token IDs and residency fingerprint. Their final
`gdn`, `tail`, `pooled`, `pooled_full`, and `kv` state fields differed. The
repeat took 3,236.6 seconds; minimum available memory was 7,005,208,576 bytes
(6.52 GiB), above the 6 GiB guard. Energy was not measured and clocks were not
controlled.

## Repeated cross-backend pattern

The first material cross-backend divergence recurred at the same sampled
boundary and with nearly identical magnitude:

| Accepted position | First material layer, first pair | Relative L2, first pair | First material layer, repeat | Relative L2, repeat |
| ---: | ---: | ---: | ---: | ---: |
| 163840 (prompt boundary) | 12 | `1.16942e-4` | 12 | `1.16942e-4` |
| 163862 | 4 | `3.25547e-3` | 4 | `3.25489e-3` |
| 163885 | 4 | `2.82868e-3` | 4 | `2.82861e-3` |

At the two generated positions, model layer 0 matched bitwise and differences
at layers 1–2 remained at float32 rounding scale. The first material delta at
layer 4 then amplified across later recurrent layers. This initially appears
to reproduce the same onset. However, the full capture hashes show that the
onset cannot yet be attributed to the backend label.

## Run-to-run crossover

The complete Strata capture from the first pair is byte-identical to the
complete NInfer capture from the repeat (SHA-256
`49ff80bf6678a1308a9c9ae472806102154aeb3a252eb2e522996db3aee0ceb7`). At the
prompt boundary, the first-pair NInfer state and repeat Strata state also match
bitwise across all 36 GDN layers. At generated positions, those latter two
states diverge only later: their first material delta is layer 36 at position
163862 (relative L2 `5.595e-3`) and layer 21 at 163885 (`1.482e-3`).

Thus the pairwise layer-4 split appears in both paired runs, but the exact
captured trajectory associated with that split switches between the backend
labels across runs. The state variation tracks the run/arm realization at
least as strongly as the backend in this small sample. Treat this as a
repeatability/correctness issue, not evidence that either backend owns the
early divergence. Matching output tokens and residency do not remove this
state-level discrepancy. No arithmetic or backend change is justified.

Next inspect arm-order and process-initialization effects with a controlled
alternating-order pair, preserving the same model, prompt, residency policy,
and accepted positions. Keep capture settings fixed and compare within-backend
and cross-backend states independently. If exact-state crossover remains,
investigate shared GPU/runtime nondeterminism or capture lifecycle before
resuming operator attribution.

Raw captures, comparator JSON, logs, and supervisor samples are local-only in
`run/` and `supervisor/`. Models remain in `~/models/strata-orin-validation/`.
