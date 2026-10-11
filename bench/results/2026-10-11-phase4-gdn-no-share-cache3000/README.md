# CPU prefill share-disabled repeatability — Orin — 2026-10-11

Three independent process runs used the same 512-token Coder IQ1_M prompt,
eight-token output, Q2_0 MTP runtime, eight CPU-pool workers, and 3,903 actual
expert-cache slots with `STRATA_PREFILL_CPU_SHARE=0`. Each request emitted the
same token IDs and output hash. Full accepted-prefix token IDs, state
fingerprints and all per-GDN hashes also matched across the three processes.

The six-GiB supervisor passed; minimum host availability was 13.31 GiB. The
median prompt time was 17,555.1 ms and median total request time was 21,207.8
ms. These traced observations are not a performance comparison and are not
combined with the separate fixed-share run as paired samples. This result is a
repeatability control for this workload and cache point; it does not establish
that share-off is more accurate. See the matched
[fixed 0.5-share run](../2026-10-11-phase4-gdn-fixed-share-half-cache3000/README.md)
and the [automatic-share repeatability check](../2026-10-11-phase4-gdn-auto-share-cache3000/README.md).
