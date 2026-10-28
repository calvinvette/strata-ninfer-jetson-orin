# Ordinary-path repeated GDN state comparison

This is a second minimally instrumented paired run of the 160K Q2_0 held-out
retrieval, with final accepted-prefix GDN arrays captured at the explicit
length `163886`. It follows the earlier numeric dump pair and uses the same
prompt, workload, model profile, cache size, staged-miss policy, and backend
pair. The previous intervening repeat did not emit arrays because its default
dump target was one token beyond the accepted length; this run corrected that
target.

Both backends returned the exact expected answer and identical 47 token IDs.
Their residency fingerprints were identical within each pair and across the
two dump runs (`a02fd81e...ddf7`). In both pairs, final `gdn`, `tail`, `pooled`,
`pooled_full`, and `kv` state fingerprints differed between backends; `L`,
`ple`, `dead`, and `ple_prev` matched. The harness therefore correctly reports
state-parity failure. These are correctness diagnostics, not performance
qualification.

## Numeric GDN state differences

Each comparison contains 36 GDN ordinals with 817,152 float32 values apiece.
The repeated same-backend comparison is important: state changes substantially
between runs even when the generated token sequence and residency map match.

| Comparison | Relative L2 | Values changed | Max absolute delta | Largest ordinal relative L2 |
| --- | ---: | ---: | ---: | ---: |
| Strata run 1 vs run 2 | `2.857e-2` | 27,510,279 / 29,417,472 (93.5%) | 1.1510 | ordinal 23: `5.617e-2` |
| NInfer run 1 vs run 2 | `2.692e-2` | 21,489,277 / 29,417,472 (73.0%) | 1.0697 | ordinal 26: `5.219e-2` |
| Strata vs NInfer, run 2 | `3.613e-2` | 27,448,406 / 29,417,472 (93.3%) | 1.4478 | ordinal 23: `7.389e-2` |

Ordinal 0 is exact across all comparisons. Strata's first material same-backend
change is ordinal 3 (relative L2 `2.829e-3`; ordinals 1–2 are at rounding
scale). NInfer matches through ordinal 9; ordinal 10 is the first material
change (relative L2 `5.493e-4`), increasing to `3.567e-3` at ordinal 11. The
cross-backend difference in run 2 is larger than either measured within-backend
run difference, but is the same order of magnitude. Run-to-run variation is
therefore a major confounder for attributing the cross-backend state delta.
This does not prove that backend arithmetic is equivalent: the observed
cross-backend difference remains, and its source is unresolved.

The arrays are end-of-request states. They do not localize when within the
160K prompt or decode the differences arise. Earlier layer captures placed the
apparent onset inconsistently, so these results do not justify changing a
backend or relaxing the exact-state contract. Next isolate repeatability at
accepted prefixes with identical token inputs and unchanged residency, then
only resume operator-level attribution if the divergence is reproducible at a
specific boundary.

## Run conditions and evidence

The pair completed in 3,236.6 seconds. Minimum available physical memory was
7,058,661,376 bytes (6.57 GiB); peak swap was 1.14 GiB; sampled OOM counters
were zero. Clocks were observed, not controlled. EMC readback and energy were
unavailable. Prompt processing took about 1,542 seconds per arm; decode took
11.45–11.63 seconds. These single diagnostic measurements are not a paired
performance result.

Raw GDN arrays, logs and supervisor samples remain local-only under `run/` and
`supervisor/`. The three compact per-ordinal comparator outputs are adjacent
JSON files. Model files remain in `~/models/strata-orin-validation/`.
