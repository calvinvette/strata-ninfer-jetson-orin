# Q2_0 cancellation and recovery under a 22-GiB cgroup cap — Orin — 2026-10-12

The current Q2_0 service ran under a transient systemd scope with
`MemoryMax=22G`, `IOAccounting=yes`, and the standard six-GiB physical/cgroup
headroom supervisor. The 2,048-token `full-chunk-2048` request was streamed
and disconnected after one second. It stopped during prompt ingestion after
512 tokens had been read, with zero output tokens. A short request in the same
service process then returned exactly `Hello Orin!`, and the server remained
alive.

The supervisor passed with minimum host `MemAvailable` of 22,914,035,712 bytes
(21.35 GiB). Its minimum effective cgroup headroom was 10,043,052,032 bytes
(9.35 GiB), above the six-GiB floor. The cgroup recorded no OOM or OOM-kill
events. The opt-in owner parser observed 304 allocations and 303 frees across
the request and recovery. At log end, only the 1,485,606,400-byte
service-lifetime weight arena remained requested-live; prefill, session,
verifier, mapped-host, pageable-stage and session-loop scratch allocations
were released. Graph-pool and driver-private memory remain outside this owner
ledger. No timing or quality claim is made.

The first scope launch dropped the user's `video`/`render` supplementary
groups and failed `NvRmMemInitNvmap`; the next used `/usr/bin/python3` and
failed because that interpreter lacks `regex`. Neither launch reached model
execution. The successful retry used `setpriv --init-groups` and the
configured user interpreter at `/home/calvin/.local/python/bin/python3`.
All attempts and their supervisor logs are retained, and only the third is
counted as a workload run.

The model was Qwen3.8 Flash-Next Q2_0 from the two local GGUF shards, with
`q2-ple-pack`, the Q2_0 expert profile, 256 requested cache slots, 4K context,
and an explicit 3,072 MiB workspace reserve. This is one bounded
cancellation/recovery point, not a general pressure guarantee. Dynamic clocks
were sampled; energy was not measured. Raw engine, cancellation, owner,
cgroup-memory, clock and tegrastats evidence is retained in this directory.
