# Q2_0 cancellation under an 18 GiB cgroup cap — pressure abort — 2026-10-11

This is a retained pressure-aborted cell for the Q2_0 cancellation/recovery
check. The long request received HTTP 200 and the client stream closed after
one second. The supervisor then stopped the process when effective cgroup
headroom fell below its required six-GiB floor, before the short recovery
request ran. The experiment scope was capped at 18 GiB; its minimum observed
remaining capacity was 6,417,248,256 bytes (5.98 GiB). Host `MemAvailable`
remained at least 22,792,822,784 bytes (21.23 GiB), so the abort was cgroup
admission pressure rather than host physical-memory pressure.

This cell does not show a recovery failure or a successful admitted run. Its
partial cancellation result, supervisor telemetry, engine log and service
config are retained here. The paired 22 GiB run that stayed above the guard
and completed recovery is documented in the sibling
[22 GiB report](../2026-10-11-phase3-q2-cancel-recovery-22G/README.md).
Artifact identity is shared with that report.
