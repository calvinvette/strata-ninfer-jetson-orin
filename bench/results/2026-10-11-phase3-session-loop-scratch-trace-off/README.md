# SessionLoopScratch trace-disabled check — Orin — 2026-10-11

The 64-KiB mapped-host lifecycle test passed with `STRATA_INTEGRATION_TRACE`
unset. Its output contained only the test success line and no owner events. The
run stayed under the six-GiB supervisor, with minimum host `MemAvailable` of
26,392,760,320 bytes (24.58 GiB). This checks the opt-in trace remains silent
when disabled; raw output and supervisor telemetry are in `supervisor/`.
