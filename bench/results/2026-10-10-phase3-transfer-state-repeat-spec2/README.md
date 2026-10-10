# MTP-off same-mode state repeat — Orin — 2026-10-10

This control repeats the exact 512-token/64-output request twice with mapped
expert reads, using the minimal `spec2` configuration without MTP. It was run
under the six-GiB supervisor; minimum available physical memory was
8,003,145,728 bytes (7.45 GiB).

Both processes emitted identical token IDs and each offered three drafts with
zero accepted. The full persistent-state fingerprints nevertheless differed
for GDN, PLE, tail, pooled, pooled-full and KV. Per-GDN-block fingerprints
matched only for the first of 36 blocks; these retain just 16 hash bits and are
diagnostic locators, not the parity test. This confirms that the observed state
instability also occurs with MTP disabled. The raw request logs and exact
records are retained in `experiment/`.
