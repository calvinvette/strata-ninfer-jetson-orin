# Q2_0 cancellation and recovery under cgroup pressure — Orin — 2026-10-11

This run tests the Q2_0 native service under a 22 GiB `MemoryMax` cgroup scope
with the standard six-GiB effective-availability supervisor. The streamed
2,048-token `full-chunk-2048` request was disconnected after one second. The
engine stopped during prompt ingestion after reading 512 of 2,048 tokens,
generated zero tokens, and logged the request as cancelled. A subsequent
request in the same service process returned the exact expected text,
`Hello Orin!`; the service remained alive. This establishes prompt-cancel
cleanup and short recovery under this cgroup cap, not recovery after a
completed long request or cancellation at other prompt boundaries.

The supervisor passed with minimum physical `MemAvailable` of
22,887,116,800 bytes (21.32 GiB). The experiment scope was capped at
23,622,320,128 bytes (22 GiB); its sampled minimum remaining capacity was
12,507,779,072 bytes (11.65 GiB). The process emitted 642 integration events;
all 302 observed allocation/free pairs balanced across expert cache,
pageable expert staging, prefill, session, verifier and mapped host staging.
Owner traces do not account for all driver or graph-pool memory. No performance
or quality claim is made.

The adjacent 18 GiB trial is retained in
[`18G-rerun/`](../2026-10-11-phase3-q2-cancel-recovery-18G-rerun/). It closed
the client stream but the effective cgroup headroom reached 6,417,248,256
bytes (5.98 GiB), below the six-GiB guard, before the short recovery check
could run. The
supervisor pressure-aborted that cell; it is not a recovery failure or a
successful admitted run. The earlier setup attempt with a missing config path
is also retained and excluded.

The Q2_0 model shard identities are recorded in the adjacent
[`artifact-identities.json`](artifact-identities.json).
The candidate engine SHA256 was
`3ef80984af6f7bfee98cddeb1853b9a36be7e642d7c6ae5f2f810b4418a85f22`; the
2048-token workload SHA256 was
`0f908c499bfa9625d9da269803332502709806bac3782e7a61ddc70e8cb8ec7c`.
Service log, config, cancellation result and supervisor telemetry are retained
in this directory; models remain in `~/models/`.

The 22 GiB command was run in a transient systemd user scope with
`MemoryMax=22G`; the inner `run_control.py` kept the physical-availability
floor at six GiB. The long workload and harness are
`bench/results/2026-10-09-phase3-fullchunk-2048/workloads.json` and
`tools/integration/cancel_long_prefill_recovery.py`.
