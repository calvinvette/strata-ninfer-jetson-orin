# Repeated reversed-order accepted-prefix GDN comparison

This repeated the NInfer-first pair in the
[first reversed-order report](../gdn-commit-all-3pos-reversed/README.md),
with the same 160K Q2_0 task, model, context, cache settings, and capture
positions. Both backends again returned the exact answer, all 47 matching
token IDs, and identical residency. Final persistent state still differed.
The run took 3,231.7 seconds; minimum available memory was 7,097,225,216 bytes
(6.61 GiB), above the 6 GiB guard. Peak sampled swap was 5.24 GiB. Clocks were
observed but not controlled; energy was not measured.

## Within-pair state comparison

| Accepted position | First exact difference | First layer at rel-L2 >= 1e-6 | Relative L2 there |
| ---: | ---: | ---: | ---: |
| 163840 (prompt boundary) | model layer 40 | none | below `1e-6` |
| 163862 | model layer 1 | model layer 4 | `3.255e-3` |
| 163885 | model layer 1 | model layer 4 | `3.196e-3` |

This does not reproduce the first reversed-order pair's generated-prefix
onsets (layers 8 and 5). It does retain near-bitwise prompt-boundary parity,
with only a sub-threshold difference at the final sampled layer.

## Across-run comparison

Comparing each backend with its own capture in the first reversed-order pair
shows run-to-run state changes. At the prompt boundary, both backends first
show a material difference at model layer 12 (relative L2 `1.169e-4`). For
generated positions, the first material same-backend differences varied:
NInfer at layers 8 and 2, and Strata at layers 4 and 2, for positions 163862
and 163885 respectively. Thus prompt-boundary parity within the reverse-order
pairs coexists with measurable run-to-run state drift, and the generated
onset is not stable across the two reverse-order pairs.

The reverse-order trial plus its repeat therefore suggests that arm order
may affect cross-backend prompt-boundary alignment, but does not establish a
causal order effect. The generated-prefix boundary moves between pairs, and
same-backend trajectories also change across runs. Preserve the exact-state
failure; do not change backend arithmetic. Next isolate process initialization
and run-to-run variation with a small pre-registered control matrix before
resuming operator localization.

The paired harness failed only persistent-state parity; inspect `run/results.json`.
Raw commit files, comparator JSON, logs and supervisor samples remain
local-only in `run/` and `supervisor/`. Models remain in
`~/models/strata-orin-validation/`.
