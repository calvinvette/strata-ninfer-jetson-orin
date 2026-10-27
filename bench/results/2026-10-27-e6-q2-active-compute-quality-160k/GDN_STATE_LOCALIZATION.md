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

Next localization step: capture committed layer-2 state at sparse positions across the long prompt (64K, 128K, 150K, 160K and accepted completion), then narrow the interval where relative L2 first grows. Keep the memory guard in place and do not infer equivalence from final text.
