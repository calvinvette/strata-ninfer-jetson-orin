# E6 160K ordinary-path GDN numerical comparison

## Outcome

This paired staged Strata/strict-NInfer Q2_0 retrieval ran with no per-token
diagnostic capture. It wrote each backend's accepted-prefix GDN state after
generation for numerical comparison. Both arms produced identical token IDs,
the exact expected 47-token answer, and the same residency fingerprint. The
final state comparison still fails in `gdn`, `tail`, `pooled`, `pooled_full`,
and `kv`; `L`, `ple`, `dead`, and `ple_prev` match.

The 36 GDN ordinals contain 817,152 float32 values each. Comparing the final
arrays shows:

| GDN ordinal | Model layer | Relative L2 | Maximum absolute delta | Values changed |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 / 817,152 |
| 1 | 1 | 5.98e-10 | 1.49e-8 | 91,270 / 817,152 |
| 2 | 2 | 1.09e-9 | 2.98e-8 | 128,324 / 817,152 |
| 3 | 4 | 2.985e-3 | 0.0177 | 817,138 / 817,152 |
| 26 | 34 | 6.730e-2 | 0.841 | 817,152 / 817,152 |
| All 36 | — | 3.042e-2 | 0.841 | 27,185,540 / 29,417,472 |

GDN ordinal 3 is model layer 4 because full-attention QSA layers occur every
fourth model layer. The first two nonzero ordinal differences are at rounding
scale in the final arrays; the first large difference is at ordinal 3, and
later state differences are much larger. This is an end-of-request comparison:
it does not establish where or when during the 163,840-token prompt the values
first diverged. The earlier layer-8 capture results remain instrumentation-
sensitive, so this measurement alone does not identify a backend defect or
justify a code change.

## Conditions

The prompt had 163,840 tokens, content SHA256
`8377a1053405efb5ca733be15d3e3a70d7586195a88c1db8b4655d6375a7cd94`, and
token-ID SHA256
`6d38b36ee0a8a2c33930db06c0db110cb510b446738640bf26891808990fc302`. The pair
took 53.86 minutes. Minimum available memory was 6.66 GiB, peak swap 1.39 GiB,
and sampled OOM kills were zero. Clocks were observed only; energy was not
measured. This is a correctness diagnostic, not a performance result.

The 113 MiB GDN dumps and raw logs remain local-only and are not committed.
