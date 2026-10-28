# Accepted-prefix GDN commit comparison at three positions

This diagnostic paired the Strata and strict NInfer expert backends on the
same 160K Q2_0 held-out retrieval with all-layer GDN commit capture at accepted
positions 163840, 163862, and 163885. Both arms used the same prompt, model,
configuration, generated answer, 47 token IDs, and residency fingerprint
(`a02fd81e...ddf7`). Final persistent state differed in `gdn`, `tail`,
`pooled`, `pooled_full`, and `kv`; the harness therefore exited with its
expected state-parity failure. This is a single diagnostic pair, not a
repeatability result or a performance qualification.

## Accepted-prefix state comparison

Each position contains 36 model GDN layers, each with 817,152 float32 values.
The first exact difference and first difference above relative L2 `1e-6` were:

| Accepted position | Token ID | First exact difference | First layer at rel-L2 >= 1e-6 | First material rel-L2 |
| ---: | ---: | ---: | ---: | ---: |
| 163840 (prompt boundary) | 19910 | model layer 12 | model layer 12 | `1.169e-4` |
| 163862 | 12 | model layer 1 | model layer 4 | `3.255e-3` |
| 163885 | 23 | model layer 1 | model layer 4 | `2.829e-3` |

At 163840, layers 0–10 matched bitwise. At 163862 and 163885, layer 0
matched bitwise; the differences at layers 1–2 were at float32 rounding scale
(relative L2 at most `1.84e-9`, max absolute delta at most `5.96e-8`). At the
next sampled layer, layer 4, the state delta was already material. Differences
then grew through later recurrent layers; the largest sampled relative L2 was
`1.263e-1` at layer 36 at position 163862. This is consistent with small
upstream numerical differences amplifying through recurrent state, but this
single pair does not identify their cause or establish that the sampled onset
is repeatable.

These captures advance the localization beyond final-state dumps: the first
selected generated prefixes are close at the first two GDN layers, then show a
clear split by model layer 4. The prompt-boundary state is already different
by layer 12. They do not show where within the long prompt earlier drift began,
and the earlier diagnostic traces produced inconsistent apparent onsets.
Repeat the exact same positions and capture settings before assigning a stable
boundary. Keep backend changes gated on repeatable localization and independent
operator evidence.

## Run conditions and files

The paired run took 3,232.6 seconds. Minimum available memory was
6,986,547,200 bytes (about 6.51 GiB), above the 6 GiB guard. Capture files are
353,014,848 bytes per backend. The run-control wrapper reports only that the
command exited nonzero; inspect the harness result for the state-parity reason.
Clocks were observed, not controlled; energy was not measured.

The raw commit captures, comparator JSON, logs and supervisor samples remain
local-only in `run/` and `supervisor/`. Model files remain in
`~/models/strata-orin-validation/`.
