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
