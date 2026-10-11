# Fixed 0.5 CPU prefill share repeatability — Orin — 2026-10-11

Three independent process runs used the same 512-token Coder IQ1_M prompt,
eight-token output, Q2_0 MTP runtime, eight CPU-pool workers, and 3,903 actual
expert-cache slots with `STRATA_PREFILL_CPU_SHARE=0.5`. Each request emitted
the same token IDs and output hash. Full accepted-prefix token IDs, state
fingerprints and all per-GDN hashes also matched across the three processes.

The six-GiB supervisor passed; minimum host availability was 13.11 GiB. The
median prompt time was 10,584.7 ms and median total request time was 14,225.4
ms. These traced observations are not a performance comparison and are not
combined with the separate share-off run as paired samples. This result shows
within-policy repeatability at this cache capacity; it does not establish
accuracy relative to share-off or qualify task quality. See the matched
[share-disabled control](../2026-10-11-phase4-gdn-no-share-cache3000/README.md)
and the [automatic-share repeatability check](../2026-10-11-phase4-gdn-auto-share-cache3000/README.md).
