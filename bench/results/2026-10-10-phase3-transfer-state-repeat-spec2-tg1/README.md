# One-token MTP-off auto-cache repeat — Orin — 2026-10-10

Two mapped requests used a 512-token prompt, one generated token, and the same
`spec2` configuration without MTP. Both emitted the same token and their 36
GDN prefill subhashes matched. Auto cache sizing selected 5,602 versus 5,634
expert slots; the requests recorded 345 versus 346 cache hits. After generation,
GDN, tail, pooled, pooled-full and KV state fingerprints differed, while PLE
and `ple_prev` matched. Minimum physical availability was 9,524,039,680 bytes
(8.87 GiB).

The first differing 16-bit GDN block subhash was ordinal 10. It is a locator,
not an equality measure. The [fixed-cache repeat](../2026-10-10-phase3-transfer-state-repeat-spec2-tg1-fixed-cache/README.md)
matched the same one-token workload and state exactly. Retain this run as a
failed mismatched-residency cell, not evidence of generic GDN nondeterminism.
