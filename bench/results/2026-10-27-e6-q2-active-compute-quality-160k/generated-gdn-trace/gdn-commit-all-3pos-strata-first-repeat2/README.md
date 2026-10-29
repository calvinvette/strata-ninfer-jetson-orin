# Third Strata-first accepted-prefix GDN pair

This repeats the same 160K Q2_0 paired retrieval with Strata first and strict
NInfer second, capturing all GDN layers at accepted positions 163840, 163862,
and 163885. Both arms produced the exact answer, identical 47 token IDs, and
the same residency fingerprint (`a02fd81e...ddf7`). Final `gdn`, `tail`,
`pooled`, `pooled_full`, and `kv` state fields differed, so the harness reports
state-parity failure. Runtime was 3,233.6 seconds. Minimum available memory
was 7,118,815,232 bytes (6.63 GiB), peak swap was 5.05 GiB, and sampled OOM
kills were zero. Clocks were observed but not controlled; energy was not
measured.

## Within-pair state comparison

The first two Strata-first pairs had material cross-backend differences at
layer 12 at the prompt boundary and layer 4 at both generated positions. This
third pair is substantially closer at all three sampled prefixes:

| Accepted position | First exact difference | First layer at rel-L2 >= 1e-6 | Relative L2 there |
| ---: | ---: | ---: | ---: |
| 163840 (prompt boundary) | none; all layers exact | none | `0` |
| 163862 | model layer 38 | none | below `1e-6` |
| 163885 | model layer 38 | model layer 44 | `6.598e-4` |

Thus the earlier layer-12/layer-4 cross-backend onset did not repeat in this
otherwise matched same-order pair. At positions 163840 and 163862, the
captured states were exact or remained below the `1e-6` material threshold
through all 36 GDN layers.

## Run-to-run comparison

Comparing this pair's captures to each backend's earlier Strata-first runs
shows material same-backend variation as well. At the prompt boundary, the
third pair matches its two engines bitwise, while same-backend comparisons to
the earlier pairs first become material at layer 12 (`1.169e-4`) for the first
pair and remain bitwise equal to the second pair. At position 163885, the
third Strata state differs materially from prior Strata at layer 21 or 4
depending on the earlier run; the third NInfer state first differs materially
from prior NInfer at layer 44 or 4. Exact token IDs and residency remained
unchanged.

This is strong evidence that final output and residency equality do not imply
repeatable GDN trajectories. The same-order pair itself ranges from a
layer-4/12 split in the first two runs to near-bitwise parity in this third
run. Backend attribution and operator localization are therefore confounded
by run-to-run state changes. Preserve the state-parity failure and avoid
changing arithmetic. Next isolate source of run variation with matched
single-backend repeats and a preregistered process-history/control matrix
before further operator tracing.

Raw captures, comparator JSON, logs and supervisor samples remain local-only
in `run/` and `supervisor/`. Models remain in `~/models/strata-orin-validation/`.
