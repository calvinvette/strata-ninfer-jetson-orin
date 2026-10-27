# 160K GDN state divergence localization

Date: 2026-10-27 (Orin AGX). Source: `0295db1e` (source unchanged); binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`. This diagnostic repeats the 163,840-token Q2_0 held-out task at accepted prefix length 163,886, with final GDN arrays captured from both staged grouped-compute backends.

| GDN state layer | Relative L2 (Strata vs NInfer) | Reading |
|---:|---:|---|
| 0 | 0 | Bitwise equal |
| 1 | 6.87e-10 | First tiny numeric delta |
| 2 | 3.41e-06 | Delta grows |
| 3 | 0.00441 | Strong amplification |
| 4 | 0.00414 | Remains material |
| All 36 layers | 3.5981% | 94.65% of 29,417,472 floats differ |

The answer, all 47 generated token IDs and resident map match, but the request fails final-state parity. Layer 0 GDN is exact, layer 1 first differs at very small magnitude, and the state delta grows markedly by layers 2–3. This localizes where the final state divergence becomes visible; it does not identify the operation that first caused it, establish which backend is correct, or prove the tiny layer-1 delta causes later state drift. Other final state fields (tail, pooled, pooled-full and KV) also differ.

The GDN dump run completed with checker failure as expected. Minimum sampled available RAM was 6.47 GiB and peak swap was 5.63 GiB; the six-GiB floor remained satisfied and OOM counters were zero. The run is not performance evidence. Full arrays and comparator output are retained locally under `gdn-dump-exacttarget/`; the 226 MiB binary dumps are deliberately not committed. Summary metrics are in `gdn-dump-exacttarget/gdn-summary.json`.

## Generated-token trace

A paired follow-up captured layer-2 GDN intermediates for generated positions
163840–163885 (46 records; terminal position 163886 had no regular GDN
intermediate record). Both arms still returned the exact answer, identical 47
token IDs and the same resident map; final state differed in the same five
fields. Minimum sampled available memory was 6.70 GiB, above the 6-GiB floor;
peak swap was about 4.7 GiB. This diagnostic is not performance evidence.

At the first generated position (163840), inputs and all captured intermediates
except `y` were bitwise equal. The `y` arrays differed in 579/6,144 values,
with max absolute delta `5.96e-8` and relative L2 `2.50e-8`; `gdn_out` and the
captured FFN values were still exact. First observed differences in other
segments appeared at position 163849 (`x`, `gate`, `beta`, `ffn_x`, `ffn_y`),
then at 163877 (`qkv`, `h`, `z`, `gdn_out`), where `x` relative L2 was
`6.88e-4` and `gdn_out` relative L2 was `4.68e-3`. At position 163885,
`gdn_out` relative L2 was `9.59e-4` and `ffn_y` relative L2 was `3.86e-3`.
The full compact per-position metrics are in
[`generated-token-trace-summary.json`](generated-gdn-trace/generated-token-trace-summary.json);
raw diagnostic arrays remain local.

This narrows the first observed divergence to the layer-2 `y` output during
generation, following bitwise-equal layer-2 state at the prompt boundary
(position 163839). It does not establish that `y` is the underlying cause,
because the tiny discrepancy may be a downstream symptom of arithmetic earlier
in the operation, nor does it establish which backend is correct. In
particular, this trace did not capture the pre-normalization `o` vector, so it
cannot distinguish a recurrence-output difference from a difference in
`gdn_out_norm`. The long-prompt checkpoint sweep is no longer the immediate next
step. Next capture `o` alongside `y` and inspect the layer-2 GDN output and
normalization paths, using a focused operator oracle before another expensive
long-context run. Keep the memory guard in place and do not infer equivalence
from final text.
