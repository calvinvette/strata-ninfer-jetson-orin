# Same-mode transfer state repeat — Orin — 2026-10-10

To isolate the failed mapped-versus-pread energy run, this control launched the
same candidate binary twice with the same 512-token prompt, 64-token output,
8K `spec4`/MTP configuration, and mapped expert reads. The six-GiB supervisor
recorded minimum `MemAvailable` of 7,871,979,520 bytes (7.33 GiB).

Both requests emitted the same 64 token IDs, with the same 34 accepted drafts
out of 87 offered. Nevertheless, their GDN, PLE, tail, pooled, pooled-full and
KV fingerprints differed. Thus the state variation occurs without changing the
transfer mode; mapped-versus-pread timing and energy comparisons must remain
unqualified until the state variation is explained. Raw engine logs and exact
state/token records are retained in `experiment/`.

This is a diagnostic failure, not evidence of a transfer regression or a user
visible output difference. The prompt/output token stream matched exactly. No
models or build products are included.

A second same-mode run enabled Strata's per-GDN-block diagnostic. Its first of
36 block fingerprints matched and the remaining 35 differed. Those per-block
fingerprints retain only 16 hash bits, so use them to locate the boundary, not
as equality evidence. The full request-level hashes and raw logs remain the
correct parity gate; this narrows follow-up work to propagation after the first
GDN state block. The refined raw run is retained in
[`2026-10-10-phase3-transfer-state-repeat-gdn`](../2026-10-10-phase3-transfer-state-repeat-gdn/).
