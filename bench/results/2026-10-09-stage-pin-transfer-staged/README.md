# Auto-cache staged-path attempt — paired capacity mismatch

This run used `STRATA_IO_PREFETCH=1` and `STRATA_IO_PF_STAGE=1`, so the trace
observed both pageable and pinned host staging. Both arms emitted the same
64-token output, but persistent state differed across six fields. Automatic
cache sizing also selected different capacities between the arms, so it cannot
isolate the staging mode. The supervisor kept minimum available memory at
7,632,564,224 bytes (7.11 GiB), above the six-GiB floor.

The run is retained as a failed comparison, not used for the fixed-cache timing
screen. See the [completed three-pair screen](../2026-10-09-stage-pin-transfer-fixed/README.md).
