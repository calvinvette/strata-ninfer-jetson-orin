# Third NInfer-first accepted-prefix GDN pair

This repeats the 160K Q2_0 paired retrieval with NInfer first, strict NInfer
backend enabled, and Strata second. All GDN layers were captured at accepted
positions 163840, 163862, and 163885. Both arms returned the expected answer,
identical 47 generated token IDs, and the same residency fingerprint
(`a02fd81e...ddf7`). Final persistent state did not match, so this remains a
correctness failure. Runtime was 3,242.0 seconds; minimum available memory was
7,141,662,720 bytes (6.65 GiB). Clocks were observed but not controlled; energy
was not measured.

## Within-pair state comparison

| Accepted position | First layer at relative L2 >= 1e-6 | Relative L2 |
| ---: | ---: | ---: |
| 163840 (prompt boundary) | 12 | `1.1694e-4` |
| 163862 | 8 | `3.2365e-3` |
| 163885 | 4 | `2.9846e-3` |

The prompt-boundary delta returned in this pair, while the two preceding
NInfer-first pairs were below threshold there. Generated-prefix differences
remain material but their first layer varies between runs. This adds evidence
for run-to-run GDN trajectory drift, not a stable backend-specific onset.

Raw captures, comparator JSON, logs, and supervisor samples remain local-only
in `run/` and `supervisor/`. Models remain in `~/models/strata-orin-validation/`.
