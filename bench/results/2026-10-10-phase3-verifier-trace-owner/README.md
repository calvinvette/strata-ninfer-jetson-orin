# Verifier breadcrumb mapped-host cleanup check — Orin — 2026-10-10

This repeat enables both `STRATA_INTEGRATION_TRACE=1` and
`STRATA_VERIFY_TRACE=1`, exercising the optional mapped breadcrumb ring as well
as ordinary verifier staging. The Q2_0 512-token/one-output MTP load/bind
request passed (output token 32) under the six-GiB supervisor. Minimum host
`MemAvailable` was 16,095,866,880 bytes (14.99 GiB).

The owner parser found 283 allocations and 283 frees, with zero live requested
bytes on host or device at process exit. `verifier-mapped-host` peaked at
521,352 bytes (0.497 MiB), including the mapped breadcrumb ring. Adding that
ring to the verifier's destructor host list fixed the prior unbalanced lifetime
on this opt-in diagnostic path. This request does not measure graph driver
memory, nor does it establish total physical ownership.

The [supervisor result](supervisor/result.json), engine event log in
`supervisor/stderr.txt`, and [owner accounting](owner-accounting.json) retain
the run evidence. Model and pack artifacts remain under `~/models/`.
